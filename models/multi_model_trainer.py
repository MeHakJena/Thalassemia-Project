"""
Multi-model training pipeline for Beta-Thalassemia variant pathogenicity classification.

Trains 5 models:
  1. Logistic Regression   (interpretable baseline)
  2. Random Forest         (ensemble baseline)
  3. XGBoost               (gradient boosting — likely best)
  4. LightGBM              (fast gradient boosting)
  5. MLP Neural Network    (deep learning baseline)

Target (3-class, thesis-standard):
  Pathogenic · Benign · VUS

Outputs:
  models/saved_models/model_comparison.json   — metrics + ROC data for dashboard
  models/saved_models/{name}.pkl              — individual serialised models
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, label_binarize
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, roc_curve,
)
import xgboost as xgb

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
    print("⚠  LightGBM not installed — skipping. Run: pip install lightgbm")

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
# Use enriched feature file; fall back to original if not yet generated
_FEATURES_PATH = BASE_DIR / "data" / "merged" / "master_hbb_features.csv"
_ORIGINAL_PATH = BASE_DIR / "data" / "merged" / "master_hbb_dataset.csv"
DATA_PATH = _FEATURES_PATH if _FEATURES_PATH.exists() else _ORIGINAL_PATH
MODELS_DIR = BASE_DIR / "models" / "saved_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("MULTI-MODEL TRAINING: BETA-THALASSEMIA PATHOGENICITY CLASSIFICATION")
print("=" * 70)
if DATA_PATH == _FEATURES_PATH:
    print("  ℹ Using enriched feature set (CADD, phyloP, SpliceAI, mol_consequence…)")
else:
    print("  ⚠ Enriched features not found. Run: python3 etl/feature_engineering.py")

# ── 1. Load & consolidate labels ─────────────────────────────────────────────
print("\n[1/6] Loading dataset…")
df = pd.read_csv(DATA_PATH)
df_labeled = df[df["pathogenicity"] != "Unknown"].copy()
print(f"  ✓ Total variants:   {len(df):,}")
print(f"  ✓ Labeled for ML:   {len(df_labeled):,}")


def consolidate(p: str) -> str:
    """Map 6 ClinVar classes → 3 thesis-standard classes."""
    p = str(p).lower()
    if "pathogenic" in p and "likely" not in p:
        return "Pathogenic"
    if "benign" in p:
        return "Benign"
    return "VUS"


df_labeled["target"] = df_labeled["pathogenicity"].apply(consolidate)
print("\n  3-class distribution:")
for cls, cnt in df_labeled["target"].value_counts().items():
    print(f"    {cls:<15}: {cnt:4d}")

# ── 2. Feature engineering ───────────────────────────────────────────────────
print("\n[2/6] Preparing features…")

# Categorical columns that need label encoding
cat_cols = ["mutation_class", "variant_type", "mol_consequence", "vep_annotation"]
# Numerical columns (already on usable scales)
num_cols = [
    "allele_freq", "homozygote_count",
    "cadd_score", "phylop_score", "spliceai_score",
    "allele_count", "allele_number", "filter_pass",
    "review_stars", "has_protein_change",
    "var_length", "is_transition", "is_frameshift",
    "is_inframe_indel", "rel_pos",
]

# Keep only columns that exist in this file (graceful if using original)
cat_cols  = [c for c in cat_cols  if c in df_labeled.columns]
num_cols  = [c for c in num_cols  if c in df_labeled.columns]
all_cols  = num_cols + cat_cols

df_labeled[cat_cols] = df_labeled[cat_cols].fillna("Unknown")
df_labeled[num_cols] = df_labeled[num_cols].fillna(0)

encoders: dict = {}
for col in cat_cols:
    le = LabelEncoder()
    df_labeled[col] = le.fit_transform(df_labeled[col].astype(str))
    encoders[col] = le

target_le = LabelEncoder()
y       = target_le.fit_transform(df_labeled["target"])
classes = list(target_le.classes_)
n_cls   = len(classes)

X = df_labeled[all_cols].values
print(f"  ✓ Features : {all_cols}")
print(f"  ✓ Classes  : {classes}")

# ── 3. Train / test split ────────────────────────────────────────────────────
print("\n[3/6] Stratified 80/20 split…")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  ✓ Train: {len(X_train)}   Test: {len(X_test)}")

y_test_bin = label_binarize(y_test, classes=list(range(n_cls)))  # (n, 3)

# ── 4. Define models ─────────────────────────────────────────────────────────
models_def: dict = {
    "Logistic Regression": LogisticRegression(
        max_iter=1000, random_state=42, class_weight="balanced", C=1.0,
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=10, random_state=42,
        class_weight="balanced", n_jobs=-1,
    ),
    "XGBoost": xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.05,
        random_state=42, tree_method="hist", verbosity=0,
        eval_metric="mlogloss",
    ),
    "MLP Neural Network": MLPClassifier(
        hidden_layer_sizes=(128, 64, 32), activation="relu",
        max_iter=500, random_state=42,
        early_stopping=True, validation_fraction=0.1,
    ),
}

if HAS_LGBM:
    models_def["LightGBM"] = lgb.LGBMClassifier(
        n_estimators=200, random_state=42,
        class_weight="balanced", verbose=-1,
    )

# ── 5. Train, evaluate, save ─────────────────────────────────────────────────
print("\n[4/6] Training & evaluating…\n")
FPR_GRID = np.linspace(0, 1, 100)
results: list  = []
roc_data: dict = {}

for name, model in models_def.items():
    print(f"  → {name}")
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)   # (n_test, n_cls)

    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec  = recall_score(y_test, y_pred,    average="weighted", zero_division=0)
    f1   = f1_score(y_test, y_pred,        average="weighted", zero_division=0)
    auc  = roc_auc_score(y_test_bin, y_proba, average="macro", multi_class="ovr")
    cm   = confusion_matrix(y_test, y_pred).tolist()

    print(f"    Acc={acc:.3f}  Prec={prec:.3f}  Rec={rec:.3f}  "
          f"F1={f1:.3f}  AUC={auc:.3f}")

    results.append({
        "model":            name,
        "accuracy":         round(float(acc),  4),
        "precision":        round(float(prec), 4),
        "recall":           round(float(rec),  4),
        "f1_score":         round(float(f1),   4),
        "roc_auc":          round(float(auc),  4),
        "confusion_matrix": cm,
    })

    # Macro-averaged ROC (interpolated onto shared FPR grid)
    mean_tpr = np.zeros_like(FPR_GRID)
    for i in range(n_cls):
        fpr_i, tpr_i, _ = roc_curve(y_test_bin[:, i], y_proba[:, i])
        mean_tpr += np.interp(FPR_GRID, fpr_i, tpr_i)
    mean_tpr /= n_cls

    roc_data[name] = {
        "tpr": [round(float(v), 4) for v in mean_tpr],
        "auc": round(float(auc), 4),
    }

    # Serialise individual model + encoder bundle
    fname = MODELS_DIR / f"{name.lower().replace(' ', '_')}.pkl"
    with open(fname, "wb") as fh:
        pickle.dump({
            "model":          model,
            "encoders":       encoders,
            "target_classes": classes,
            "features":       all_cols,
        }, fh)
    print(f"    Saved → {fname.name}\n")

# ── 6. Compile & persist comparison JSON ─────────────────────────────────────
results.sort(key=lambda x: x["roc_auc"], reverse=True)

comparison = {
    "classes":       classes,
    "feature_names": all_cols,
    "n_train":       int(len(X_train)),
    "n_test":        int(len(X_test)),
    "trained_at":    datetime.now().isoformat(),
    "metrics":       results,
    "roc_fpr_grid":  [round(float(v), 4) for v in FPR_GRID],
    "roc_curves":    roc_data,
}

out_path = MODELS_DIR / "model_comparison.json"
with open(out_path, "w") as fh:
    json.dump(comparison, fh, indent=2)

print(f"[5/6] Saved → {out_path}")

# ── Print leaderboard ─────────────────────────────────────────────────────────
medals = ["🥇", "🥈", "🥉", "4 ", "5 "]
print("\n" + "=" * 70)
print("✅ TRAINING COMPLETE — LEADERBOARD (sorted by ROC-AUC)")
print("=" * 70)
print(f"  {'':5} {'Model':<25} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}")
print("  " + "-" * 60)
for i, r in enumerate(results):
    m = medals[i] if i < len(medals) else f"{i+1} "
    print(
        f"  {m} {r['model']:<23} "
        f"{r['accuracy']:>6.3f} {r['precision']:>6.3f} "
        f"{r['recall']:>6.3f} {r['f1_score']:>6.3f} {r['roc_auc']:>6.3f}"
    )
print()
print(f"  Dashboard data: {out_path}")
