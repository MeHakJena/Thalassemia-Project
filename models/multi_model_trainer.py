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
  data/merged/external_validation_cohort.csv  — The independent 10% holdout set
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
from sklearn.model_selection import train_test_split, StratifiedKFold
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
_FEATURES_PATH = BASE_DIR / "data" / "merged" / "master_hbb_features.csv"
_ORIGINAL_PATH = BASE_DIR / "data" / "merged" / "master_hbb_dataset.csv"
DATA_PATH = _FEATURES_PATH if _FEATURES_PATH.exists() else _ORIGINAL_PATH
MODELS_DIR = BASE_DIR / "models" / "saved_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
HOLDOUT_PATH = BASE_DIR / "data" / "merged" / "external_validation_cohort.csv"

print("=" * 70)
print("MULTI-MODEL TRAINING: K-FOLD CV & INDEPENDENT VALIDATION")
print("=" * 70)

# ── 1. Load & consolidate labels ─────────────────────────────────────────────
print("\n[1/6] Loading dataset…")
df = pd.read_csv(DATA_PATH)
df_labeled = df[df["pathogenicity"] != "Unknown"].copy()
print(f"  ✓ Total variants:   {len(df):,}")
print(f"  ✓ Labeled for ML:   {len(df_labeled):,}")

def consolidate(p: str) -> str:
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
cat_cols = ["mutation_class", "variant_type", "mol_consequence", "vep_annotation"]
num_cols = [
    "allele_freq", "homozygote_count", "cadd_score", "phylop_score", "spliceai_score",
    "allele_count", "allele_number", "filter_pass", "review_stars", "has_protein_change",
    "var_length", "is_transition", "is_frameshift", "is_inframe_indel", "rel_pos",
]

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

# ── 3. Independent Holdout (External Cohort Simulation) ──────────────────────
print("\n[3/6] Creating Independent Validation Cohort (10% holdout)…")
# We hold out 10% completely before cross-validation
indices = np.arange(len(X))
X_cv, X_holdout, y_cv, y_holdout, idx_cv, idx_holdout = train_test_split(
    X, y, indices, test_size=0.10, random_state=42, stratify=y
)

# Save the holdout set to simulate an external lab cohort
df_holdout = df_labeled.iloc[idx_holdout]
df_holdout.to_csv(HOLDOUT_PATH, index=False)
print(f"  ✓ CV Train Set: {len(X_cv)} samples")
print(f"  ✓ Holdout Validation Set: {len(X_holdout)} samples (Saved to external_validation_cohort.csv)")

y_holdout_bin = label_binarize(y_holdout, classes=list(range(n_cls)))

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

# ── 5. 5-Fold Cross Validation & Final Training ──────────────────────────────
print("\n[4/6] Running 5-Fold Cross Validation & Final Evaluation…\n")
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
FPR_GRID = np.linspace(0, 1, 100)
results: list = []
roc_data: dict = {}

for name, model in models_def.items():
    print(f"  → {name}")
    
    cv_acc, cv_prec, cv_rec, cv_f1, cv_auc = [], [], [], [], []
    
    # K-Fold CV
    for train_idx, val_idx in skf.split(X_cv, y_cv):
        X_fold_train, X_fold_val = X_cv[train_idx], X_cv[val_idx]
        y_fold_train, y_fold_val = y_cv[train_idx], y_cv[val_idx]
        
        # Clone model to avoid bleeding state
        from sklearn.base import clone
        fold_model = clone(model)
        fold_model.fit(X_fold_train, y_fold_train)
        
        y_fold_pred = fold_model.predict(X_fold_val)
        y_fold_proba = fold_model.predict_proba(X_fold_val)
        y_fold_val_bin = label_binarize(y_fold_val, classes=list(range(n_cls)))
        
        cv_acc.append(accuracy_score(y_fold_val, y_fold_pred))
        cv_prec.append(precision_score(y_fold_val, y_fold_pred, average="weighted", zero_division=0))
        cv_rec.append(recall_score(y_fold_val, y_fold_pred, average="weighted", zero_division=0))
        cv_f1.append(f1_score(y_fold_val, y_fold_pred, average="weighted", zero_division=0))
        cv_auc.append(roc_auc_score(y_fold_val_bin, y_fold_proba, average="macro", multi_class="ovr"))
        
    # Final Model Training (on all CV data) & Test on Holdout
    model.fit(X_cv, y_cv)
    y_holdout_pred = model.predict(X_holdout)
    y_holdout_proba = model.predict_proba(X_holdout)
    
    holdout_acc = accuracy_score(y_holdout, y_holdout_pred)
    holdout_auc = roc_auc_score(y_holdout_bin, y_holdout_proba, average="macro", multi_class="ovr")
    cm = confusion_matrix(y_holdout, y_holdout_pred).tolist()
    
    print(f"    CV 5-Fold Acc = {np.mean(cv_acc):.3f} ± {np.std(cv_acc):.3f}")
    print(f"    Holdout Acc   = {holdout_acc:.3f}  Holdout AUC = {holdout_auc:.3f}")
    
    results.append({
        "model": name,
        "cv_accuracy": {"mean": round(float(np.mean(cv_acc)), 4), "std": round(float(np.std(cv_acc)), 4)},
        "cv_precision": {"mean": round(float(np.mean(cv_prec)), 4), "std": round(float(np.std(cv_prec)), 4)},
        "cv_recall": {"mean": round(float(np.mean(cv_rec)), 4), "std": round(float(np.std(cv_rec)), 4)},
        "cv_f1_score": {"mean": round(float(np.mean(cv_f1)), 4), "std": round(float(np.std(cv_f1)), 4)},
        "cv_roc_auc": {"mean": round(float(np.mean(cv_auc)), 4), "std": round(float(np.std(cv_auc)), 4)},
        "holdout_accuracy": round(float(holdout_acc), 4),
        "holdout_roc_auc": round(float(holdout_auc), 4),
        "confusion_matrix": cm,
        # Maintain original flat keys for backwards compatibility in frontend if needed
        "accuracy": round(float(np.mean(cv_acc)), 4),
        "roc_auc": round(float(np.mean(cv_auc)), 4),
    })
    
    # Macro-averaged ROC (interpolated onto shared FPR grid) for Holdout
    mean_tpr = np.zeros_like(FPR_GRID)
    for i in range(n_cls):
        fpr_i, tpr_i, _ = roc_curve(y_holdout_bin[:, i], y_holdout_proba[:, i])
        mean_tpr += np.interp(FPR_GRID, fpr_i, tpr_i)
    mean_tpr /= n_cls

    roc_data[name] = {
        "tpr": [round(float(v), 4) for v in mean_tpr],
        "auc": round(float(holdout_auc), 4),
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
results.sort(key=lambda x: x["cv_roc_auc"]["mean"], reverse=True)

comparison = {
    "classes":       classes,
    "feature_names": all_cols,
    "n_cv_samples":  int(len(X_cv)),
    "n_holdout":     int(len(X_holdout)),
    "n_folds":       5,
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
print("✅ TRAINING COMPLETE — LEADERBOARD (sorted by CV ROC-AUC)")
print("=" * 70)
print(f"  {'':5} {'Model':<25} {'CV Acc ± Std':>15} {'Holdout AUC':>12}")
print("  " + "-" * 60)
for i, r in enumerate(results):
    m = medals[i] if i < len(medals) else f"{i+1} "
    print(
        f"  {m} {r['model']:<23} "
        f"{r['cv_accuracy']['mean'] * 100:>6.1f}% ± {r['cv_accuracy']['std'] * 100:>4.1f}% "
        f"{r['holdout_roc_auc']:>10.3f}"
    )
print()
print(f"  Dashboard data: {out_path}")
