"""
Train XGBoost pathogenicity classifier on REAL genomic data
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import pickle
import os

print("=" * 80)
print("TRAINING XGBOOST ON REAL HBB GENOMIC DATA")
print("=" * 80)

# Load master dataset
print("\n[1/5] Loading master HBB dataset...")
df = pd.read_csv('data/merged/master_hbb_dataset.csv')

# Filter to variants with known pathogenicity
train_df = df[df['pathogenicity'] != 'Unknown'].copy()
print(f"  ✓ Loaded {len(df):,} total variants")
print(f"  ✓ Using {len(train_df):,} variants with known pathogenicity for training")

print("\n[2/5] Preparing features and labels...")

# Target: pathogenicity
y_raw = train_df['pathogenicity'].values

# Features
cat_cols = ['mutation_class', 'variant_type']
num_cols = ['allele_freq', 'homozygote_count']

# Handle missing values
train_df[cat_cols] = train_df[cat_cols].fillna('Unknown')
train_df[num_cols] = train_df[num_cols].fillna(0)

# Encode categorical features
encoders = {}
for col in cat_cols:
    le = LabelEncoder()
    train_df[col] = le.fit_transform(train_df[col].astype(str))
    encoders[col] = le

# Encode target
target_le = LabelEncoder()
y = target_le.fit_transform(y_raw)
encoders['target'] = target_le

X = train_df[num_cols + cat_cols].copy()

print(f"  ✓ Features: {num_cols + cat_cols}")
print(f"  ✓ Target classes: {target_le.classes_}")
print(f"  ✓ Class distribution:\n{pd.Series(y).value_counts().sort_index()}")

print("\n[3/5] Splitting data (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"  ✓ Train: {len(X_train)} variants")
print(f"  ✓ Test: {len(X_test)} variants")

print("\n[4/5] Training XGBoost model...")
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    tree_method='hist',
    verbose=0
)

model.fit(X_train, y_train)

print(f"  ✓ Model trained")

print("\n[5/5] Evaluating model...")
train_score = model.score(X_train, y_train)
test_score = model.score(X_test, y_test)

y_pred = model.predict(X_test)

print(f"  ✓ Train Accuracy: {train_score:.4f}")
print(f"  ✓ Test Accuracy: {test_score:.4f}")

print(f"\nClassification Report (Test Set):")
print(classification_report(y_test, y_pred, target_names=target_le.classes_))

# Save model
os.makedirs('models/saved_models', exist_ok=True)
model_path = 'models/saved_models/pathogenicity_model_real_data.pkl'

with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'encoders': encoders,
        'features': num_cols + cat_cols
    }, f)

print("\n" + "=" * 80)
print("✅ MODEL TRAINING COMPLETE")
print("=" * 80)
print(f"\nModel saved: {model_path}")
print(f"Ready for: API inference → Dashboard predictions → Clinical interpretation")

# Feature importance
print(f"\n📊 FEATURE IMPORTANCE")
importance_df = pd.DataFrame({
    'feature': num_cols + cat_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(importance_df.to_string(index=False))
