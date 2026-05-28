"""
Hyperparameter tuning for XGBoost pathogenicity classifier
Use GridSearchCV and class weights to improve performance
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
import pickle
import os

print("=" * 80)
print("HYPERPARAMETER TUNING: XGBOOST PATHOGENICITY CLASSIFIER")
print("=" * 80)

# Load master dataset
print("\n[1/6] Loading and preparing data...")
df = pd.read_csv('data/merged/master_hbb_dataset.csv')
train_df = df[df['pathogenicity'] != 'Unknown'].copy()

# Features & target
cat_cols = ['mutation_class', 'variant_type']
num_cols = ['allele_freq', 'homozygote_count']

train_df[cat_cols] = train_df[cat_cols].fillna('Unknown')
train_df[num_cols] = train_df[num_cols].fillna(0)

# Encode
encoders = {}
for col in cat_cols:
    le = LabelEncoder()
    train_df[col] = le.fit_transform(train_df[col].astype(str))
    encoders[col] = le

target_le = LabelEncoder()
y = target_le.fit_transform(train_df['pathogenicity'])
encoders['target'] = target_le

X = train_df[num_cols + cat_cols].copy()

print(f"  ✓ Dataset: {len(X)} variants")
print(f"  ✓ Target classes: {target_le.classes_}")
print(f"  ✓ Class distribution:")
for cls, count in zip(target_le.classes_, np.bincount(y)):
    print(f"    - {cls:20s}: {count:4d}")

# Compute class weights to handle imbalance
class_weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
sample_weights = class_weights[y]

print(f"\n  ✓ Class weights (for imbalance):")
for cls, weight in zip(target_le.classes_, class_weights):
    print(f"    - {cls:20s}: {weight:.3f}")

# Train-test split
print("\n[2/6] Splitting data (80/20)...")
X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
    X, y, sample_weights, test_size=0.2, random_state=42, stratify=y
)

print(f"  ✓ Train: {len(X_train)} samples")
print(f"  ✓ Test: {len(X_test)} samples")

# Grid search
print("\n[3/6] GridSearchCV - Testing hyperparameters...")
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.05, 0.1],
    'min_child_weight': [1, 3],
}

xgb_base = xgb.XGBClassifier(random_state=42, tree_method='hist')

grid_search = GridSearchCV(
    xgb_base,
    param_grid,
    cv=3,
    scoring='f1_weighted',
    n_jobs=-1,
    verbose=1
)

# Fit with class weights
grid_search.fit(X_train, y_train, sample_weight=w_train)

print(f"  ✓ Best parameters: {grid_search.best_params_}")
print(f"  ✓ Best CV F1 score: {grid_search.best_score_:.4f}")

# Train final model with best params
print("\n[4/6] Training final model with best parameters...")
best_model = grid_search.best_estimator_
best_model.fit(X_train, y_train, sample_weight=w_train)

print(f"  ✓ Model trained")

# Evaluate
print("\n[5/6] Evaluating on test set...")
train_score = best_model.score(X_train, y_train)
test_score = best_model.score(X_test, y_test)

y_pred = best_model.predict(X_test)
y_pred_proba = best_model.predict_proba(X_test)

print(f"  ✓ Train Accuracy: {train_score:.4f}")
print(f"  ✓ Test Accuracy: {test_score:.4f}")
print(f"\nClassification Report (Test Set):")
print(classification_report(y_test, y_pred, target_names=target_le.classes_))

# Compute weighted F1
f1_weighted = f1_score(y_test, y_pred, average='weighted')
f1_macro = f1_score(y_test, y_pred, average='macro')
print(f"  ✓ F1 Score (weighted): {f1_weighted:.4f}")
print(f"  ✓ F1 Score (macro): {f1_macro:.4f}")

# Save
print("\n[6/6] Saving tuned model...")
os.makedirs('models/saved_models', exist_ok=True)
model_path = 'models/saved_models/pathogenicity_model.pkl'

with open(model_path, 'wb') as f:
    pickle.dump({
        'model': best_model,
        'encoders': encoders,
        'features': num_cols + cat_cols
    }, f)

print(f"  ✓ Saved to: {model_path}")

# Feature importance
print("\n" + "=" * 80)
print("📊 FEATURE IMPORTANCE")
print("=" * 80)
importance_df = pd.DataFrame({
    'feature': num_cols + cat_cols,
    'importance': best_model.feature_importances_
}).sort_values('importance', ascending=False)

print(importance_df.to_string(index=False))

print("\n" + "=" * 80)
print("✅ TUNING COMPLETE")
print("=" * 80)
print(f"\nModel saved: {model_path}")
print(f"Ready for API deployment!")
