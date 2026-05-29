import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import json

df = pd.read_csv("data/merged/master_hbb_features.csv")
df_labeled = df[df["pathogenicity"] != "Unknown"].copy()

print("TOTAL ROWS:", len(df))
print("LABELED ROWS:", len(df_labeled))

# Raw distribution
print("\nRAW DISTRIBUTION:")
print(df_labeled["pathogenicity"].value_counts())

# Consolidated distribution
def consolidate(p):
    p = str(p).lower()
    if "pathogenic" in p and "likely" not in p: return "Pathogenic"
    if "benign" in p: return "Benign"
    return "VUS"

df_labeled["target"] = df_labeled["pathogenicity"].apply(consolidate)
print("\nCONSOLIDATED DISTRIBUTION:")
print(df_labeled["target"].value_counts())

# Missing features
print("\nMISSING VALUES (before imputation):")
print(df_labeled.isna().sum()[df_labeled.isna().sum() > 0])

# Random Forest Feature Importance
cat_cols = ["mutation_class", "variant_type", "mol_consequence", "vep_annotation"]
num_cols = ["allele_freq", "homozygote_count", "cadd_score", "phylop_score", "spliceai_score", "allele_count", "allele_number", "filter_pass", "review_stars", "has_protein_change", "var_length", "is_transition", "is_frameshift", "is_inframe_indel", "rel_pos"]
cat_cols = [c for c in cat_cols if c in df_labeled.columns]
num_cols = [c for c in num_cols if c in df_labeled.columns]
all_cols = num_cols + cat_cols

df_labeled[cat_cols] = df_labeled[cat_cols].fillna("Unknown")
df_labeled[num_cols] = df_labeled[num_cols].fillna(0)

for col in cat_cols:
    df_labeled[col] = LabelEncoder().fit_transform(df_labeled[col].astype(str))

y = LabelEncoder().fit_transform(df_labeled["target"])
X = df_labeled[all_cols].values

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

print("\nFEATURE IMPORTANCES:")
fi = sorted(zip(all_cols, rf.feature_importances_), key=lambda x: x[1], reverse=True)
for feat, imp in fi:
    print(f"  {feat}: {imp:.4f}")

print("\nTOP CORRELATIONS WITH TARGET:")
corr_df = df_labeled[all_cols].copy()
corr_df["target_encoded"] = y
corrmat = corr_df.corr()["target_encoded"].sort_values(ascending=False)
print(corrmat)

