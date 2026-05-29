import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder

# Load data
df = pd.read_csv("data/merged/master_hbb_features.csv")
df_labeled = df[df["pathogenicity"] != "Unknown"].copy()

# Consolidate target
def consolidate(p):
    p = str(p).lower()
    if "pathogenic" in p and "likely" not in p: return "Pathogenic"
    if "benign" in p: return "Benign"
    return "VUS"

df_labeled["target"] = df_labeled["pathogenicity"].apply(consolidate)

# Define columns
cat_cols = ["mutation_class", "variant_type", "mol_consequence", "vep_annotation"]
num_cols = ["allele_freq", "homozygote_count", "cadd_score", "phylop_score", "spliceai_score", "allele_count", "allele_number", "filter_pass", "review_stars", "has_protein_change", "var_length", "is_transition", "is_frameshift", "is_inframe_indel", "rel_pos"]

cat_cols = [c for c in cat_cols if c in df_labeled.columns]
num_cols = [c for c in num_cols if c in df_labeled.columns]
all_cols = num_cols + cat_cols

# Impute
df_labeled[cat_cols] = df_labeled[cat_cols].fillna("Unknown")
df_labeled[num_cols] = df_labeled[num_cols].fillna(0)

# Encode
for col in cat_cols:
    df_labeled[col] = LabelEncoder().fit_transform(df_labeled[col].astype(str))

y = LabelEncoder().fit_transform(df_labeled["target"])

# Create correlation dataframe
corr_df = df_labeled[all_cols].copy()
corr_df["target_encoded"] = y

# Calculate Pearson correlation
corrmat = corr_df.corr(method='pearson')

# Plot setup
plt.figure(figsize=(16, 12))
sns.heatmap(corrmat, cmap='coolwarm', annot=True, fmt=".2f", linewidths=0.5,
            cbar_kws={"shrink": .8}, vmin=-1, vmax=1, square=True)

plt.title('Pearson Correlation Matrix of HBB Genomic Features', fontsize=16, pad=20)
plt.tight_layout()

# Save image
plt.savefig("correlation_matrix.png", dpi=300, bbox_inches='tight')
print("Successfully generated correlation_matrix.png")
