import pandas as pd
import numpy as np

def merge_datasets():
    print("Loading cleaned datasets...")
    clinvar = pd.read_csv('../data/cleaned/clinvar_clean.csv')
    gnomad = pd.read_csv('../data/cleaned/gnomad_clean.csv')
    hbvar = pd.read_csv('../data/cleaned/hbvar_clean.csv')
    
    # Merge ClinVar and gnomAD on chr, pos, ref, alt, gene
    print("Merging ClinVar and gnomAD...")
    master_df = pd.merge(
        clinvar, 
        gnomad, 
        on=['chr', 'pos', 'ref', 'alt', 'gene'], 
        how='outer',
        suffixes=('_clinvar', '_gnomad')
    )
    
    # Consolidate dbsnp_id
    master_df['dbsnp_id'] = master_df['dbsnp_id_clinvar'].fillna(master_df['dbsnp_id_gnomad'])
    # Clean up 'nan' string
    master_df['dbsnp_id'] = master_df['dbsnp_id'].replace('nan', np.nan)
    
    # Merge HbVar based on dbsnp_id
    print("Merging HbVar...")
    hbvar['dbsnp_id'] = hbvar['dbsnp_id'].replace('nan', np.nan)
    hbvar_valid = hbvar.dropna(subset=['dbsnp_id'])
    
    # To avoid duplicate columns from outer merge
    master_df = pd.merge(
        master_df,
        hbvar_valid[['dbsnp_id', 'mutation', 'severity', 'mutation_class']],
        on='dbsnp_id',
        how='left'
    )
    
    # Fill missing severities with 'Unknown'
    master_df['severity'] = master_df['severity'].fillna('Unknown')
    master_df['pathogenicity'] = master_df['pathogenicity'].fillna('Unknown')
    master_df['variant_type'] = master_df['variant_type'].fillna('Unknown')
    master_df['allele_freq'] = master_df['allele_freq'].fillna(0.0)
    
    # Final schema: chr | pos | ref | alt | gene | pathogenicity | allele_freq | severity | variant_type
    keep_cols = [
        'chr', 'pos', 'ref', 'alt', 'gene', 
        'pathogenicity', 'allele_freq', 'severity', 'variant_type',
        'mutation_class', 'homozygote_count' # Keep for models
    ]
    
    final_df = master_df[keep_cols]
    final_df = final_df.drop_duplicates()
    
    final_df.to_csv('../data/merged/master_variant_table.csv', index=False)
    print(f"Master variant table generated: {len(final_df)} rows")
    return final_df

if __name__ == "__main__":
    merge_datasets()
