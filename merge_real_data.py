"""
Merge three genomic datasets:
1. ClinVar VCF (clinical classification)
2. gnomAD (population frequencies)
3. HbVar (severity/mutation class)
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("MERGING GENOMIC DATASETS FOR ML TRAINING")
print("=" * 80)

# Load datasets
print("\n[1/4] Loading datasets...")
clinvar_vcf = pd.read_csv('data/processed/hbb_clinvar_variants.csv')
gnomad = pd.read_csv('data/cleaned/gnomad_clean.csv')
hbvar = pd.read_csv('data/cleaned/hbvar_clean.csv')

print(f"  ✓ ClinVar VCF:  {len(clinvar_vcf)} variants")
print(f"  ✓ gnomAD:       {len(gnomad)} variants")
print(f"  ✓ HbVar:        {len(hbvar)} variants")

# Step 1: Clean ClinVar VCF clinical significance
print("\n[2/4] Normalizing clinical significance...")

def normalize_clinical_sig(sig):
    """Map ClinVar classifications to simple categories"""
    if pd.isna(sig):
        return 'Unknown'
    sig_str = str(sig).lower()
    
    if 'pathogenic' in sig_str and 'likely' not in sig_str and '|' not in sig_str:
        return 'Pathogenic'
    elif 'likely_pathogenic' in sig_str:
        return 'Likely_pathogenic'
    elif 'benign' in sig_str and 'likely' not in sig_str:
        return 'Benign'
    elif 'likely_benign' in sig_str:
        return 'Likely_benign'
    elif 'uncertain' in sig_str:
        return 'VUS'
    else:
        return 'Other'

clinvar_vcf['pathogenicity'] = clinvar_vcf['clinical_significance'].apply(normalize_clinical_sig)

# Filter: Keep only chr11 for HBB
clinvar_vcf = clinvar_vcf[clinvar_vcf['chrom'].astype(str) == '11'].copy()
clinvar_vcf['chr'] = 11
clinvar_vcf['variant_type'] = 'SNP'  # ClinVar doesn't have variant type info in extract

print(f"  ✓ Normalized clinical significance")
print(f"  ✓ Filtered to chr11 only: {len(clinvar_vcf)} variants")

# Step 2: Merge ClinVar + gnomAD on chr, pos, ref, alt
print("\n[3/4] Merging ClinVar + gnomAD...")
master = pd.merge(
    clinvar_vcf[['chr', 'pos', 'ref', 'alt', 'pathogenicity', 'variant_id', 'geneinfo', 'variant_type']],
    gnomad[['chr', 'pos', 'ref', 'alt', 'allele_freq', 'homozygote_count', 'dbsnp_id']],
    on=['chr', 'pos', 'ref', 'alt'],
    how='outer'
)

print(f"  ✓ After ClinVar + gnomAD merge: {len(master)} variants")

# Use dbsnp_id from gnomAD or variant_id from ClinVar for HbVar lookup
master['dbsnp_id'] = master['dbsnp_id'].fillna(master['variant_id'].astype(str))

# Step 3: Merge with HbVar (on dbsnp_id)
print("\n[4/4] Merging with HbVar severity...")
hbvar_clean = hbvar[['dbsnp_id', 'severity', 'mutation_class']].copy()
hbvar_clean['dbsnp_id'] = hbvar_clean['dbsnp_id'].astype(str)

master = pd.merge(
    master,
    hbvar_clean,
    on='dbsnp_id',
    how='left'
)

print(f"  ✓ After HbVar merge: {len(master)} variants")

# Fill missing values
master['pathogenicity'] = master['pathogenicity'].fillna('Unknown')
master['severity'] = master['severity'].fillna('Unknown')
master['mutation_class'] = master['mutation_class'].fillna('Unknown')
master['allele_freq'] = master['allele_freq'].fillna(0.0)
master['homozygote_count'] = master['homozygote_count'].fillna(0)
master['variant_type'] = master['variant_type'].fillna('Unknown')

# Select final columns
final_cols = [
    'chr', 'pos', 'ref', 'alt', 
    'pathogenicity', 'severity', 'mutation_class', 'variant_type',
    'allele_freq', 'homozygote_count',
    'dbsnp_id', 'geneinfo'
]

master = master[final_cols].drop_duplicates()

# Save
import os
os.makedirs('data/merged', exist_ok=True)
master.to_csv('data/merged/master_hbb_dataset.csv', index=False)

print("\n" + "=" * 80)
print("✅ MERGE COMPLETE")
print("=" * 80)
print(f"\nOutput: data/merged/master_hbb_dataset.csv")
print(f"Total variants: {len(master)}")
print(f"\nSchema:")
print(master.dtypes)
print(f"\nFirst 5 rows:")
print(master.head())
print(f"\nClinical Significance Distribution:")
print(master['pathogenicity'].value_counts())
print(f"\nSeverity Distribution:")
print(master['severity'].value_counts())
