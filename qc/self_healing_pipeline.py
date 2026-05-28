import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

def corrupt_data(df):
    """Injects synthetic errors into the dataset."""
    print("Injecting synthetic errors...")
    corrupted = df.copy()
    
    # 1. Duplicate rows (duplicate first 50 rows)
    duplicates = corrupted.head(50).copy()
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    
    # 2. Bad chromosome formats
    bad_chr_idx = np.random.choice(corrupted.index, 100, replace=False)
    corrupted['chr'] = corrupted['chr'].astype(str)
    corrupted.loc[bad_chr_idx, 'chr'] = 'chr11'
    
    # 3. Missing critical values
    missing_idx = np.random.choice(corrupted.index, 100, replace=False)
    corrupted.loc[missing_idx, 'allele_freq'] = np.nan
    
    # 4. Outliers for Isolation Forest
    outlier_idx = np.random.choice(corrupted.index, 50, replace=False)
    corrupted.loc[outlier_idx, 'allele_freq'] = 9.99  # Physically impossible freq
    corrupted.loc[outlier_idx, 'homozygote_count'] = -500 # Impossible count
    
    corrupted.to_csv('../data/merged/synthetic_corrupted_vcf.csv', index=False)
    print(f"Corrupted data saved. Shape: {corrupted.shape}")
    return corrupted

def detect_anomalies(df):
    """Detects anomalies using Isolation Forest."""
    print("Detecting anomalies...")
    
    # Prepare features for Isolation Forest
    features = ['allele_freq', 'homozygote_count']
    X = df[features].fillna(-1) # Handle nan for model
    
    # Isolation Forest
    clf = IsolationForest(contamination=0.05, random_state=42)
    df['anomaly_score'] = clf.fit_predict(X)
    
    # -1 means anomaly, 1 means normal
    anomalies = df[df['anomaly_score'] == -1]
    print(f"Detected {len(anomalies)} anomalies using Isolation Forest.")
    return df

def repair_data(df):
    """Repairs the dataset."""
    print("Repairing data...")
    repaired = df.copy()
    
    # 1. Deduplicate
    initial_len = len(repaired)
    repaired = repaired.drop_duplicates(subset=['chr', 'pos', 'ref', 'alt', 'gene'])
    print(f"Removed {initial_len - len(repaired)} duplicates.")
    
    # 2. Fix chromosome formats
    repaired['chr'] = repaired['chr'].astype(str).str.replace('chr', '')
    
    # 3. Fill missing allele_freq with median of non-anomalies
    median_af = repaired.loc[repaired['anomaly_score'] == 1, 'allele_freq'].median()
    repaired['allele_freq'] = repaired['allele_freq'].fillna(median_af)
    
    # 4. Handle anomalies (clip outliers to safe maximums or drop)
    # We will just cap impossible values
    repaired.loc[repaired['allele_freq'] > 1.0, 'allele_freq'] = median_af
    repaired.loc[repaired['homozygote_count'] < 0, 'homozygote_count'] = 0
    
    repaired.to_csv('../data/merged/trusted_variants.csv', index=False)
    print(f"Trusted variants saved. Final shape: {repaired.shape}")
    return repaired

if __name__ == "__main__":
    df = pd.read_csv('../data/merged/master_variant_table.csv')
    
    # 1. Corrupt
    corrupted_df = corrupt_data(df)
    
    # 2. Detect
    detected_df = detect_anomalies(corrupted_df)
    
    # 3. Repair
    trusted_df = repair_data(detected_df)
    print("Self-Healing QC Pipeline Complete.")
