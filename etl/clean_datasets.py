import pandas as pd
import glob
import os

def clean_clinvar():
    print("Cleaning ClinVar...")
    df = pd.read_csv('../data/raw/clinvar_result.txt', sep='\t', low_memory=False)
    # Filter for HBB
    df = df[df['Gene(s)'].astype(str).str.contains('HBB')]
    
    # Extract chr, pos, ref, alt from Canonical SPDI
    def parse_spdi(spdi):
        if pd.isna(spdi):
            return None, None, None, None
        parts = str(spdi).split(':')
        if len(parts) == 4:
            return '11', parts[1], parts[2], parts[3]
        return None, None, None, None
    
    parsed = df['Canonical SPDI'].apply(parse_spdi)
    df['chr'] = [p[0] for p in parsed]
    df['pos'] = [p[1] for p in parsed]
    df['ref'] = [p[2] for p in parsed]
    df['alt'] = [p[3] for p in parsed]
    
    df = df.dropna(subset=['pos', 'ref', 'alt'])
    
    df['gene'] = 'HBB'
    df['variant_type'] = df['Variant type']
    df['pathogenicity'] = df['Germline classification']
    df['review_status'] = df['Germline review status']
    df['dbsnp_id'] = df['dbSNP ID'].astype(str)
    
    keep_cols = ['chr', 'pos', 'ref', 'alt', 'gene', 'variant_type', 'pathogenicity', 'review_status', 'dbsnp_id']
    df = df[keep_cols]
    
    df['chr'] = df['chr'].astype(str).str.replace('chr', '')
    df['pos'] = df['pos'].astype(int)
    
    df.to_csv('../data/cleaned/clinvar_clean.csv', index=False)
    print(f"ClinVar cleaned: {len(df)} rows")
    return df

def clean_gnomad():
    print("Cleaning gnomAD...")
    files = glob.glob('../data/raw/gnomAD*.csv')
    if not files: return
    df = pd.read_csv(files[0], low_memory=False)
    
    df = df[df['Chromosome'].astype(str) == '11']
    
    df['chr'] = df['Chromosome'].astype(str).str.replace('chr', '')
    df['pos'] = df['Position'].astype(int)
    df['ref'] = df['Reference']
    df['alt'] = df['Alternate']
    df['allele_freq'] = df['Allele Frequency']
    df['homozygote_count'] = df['Homozygote Count']
    df['filter'] = df['Filters - exomes'].fillna(df['Filters - genomes'])
    df['dbsnp_id'] = df['rsIDs'].astype(str)
    
    df['gene'] = 'HBB'
    
    keep_cols = ['chr', 'pos', 'ref', 'alt', 'gene', 'allele_freq', 'homozygote_count', 'filter', 'dbsnp_id']
    df = df[keep_cols]
    
    df.to_csv('../data/cleaned/gnomad_clean.csv', index=False)
    print(f"gnomAD cleaned: {len(df)} rows")
    return df

def clean_hbvar():
    print("Cleaning HbVar...")
    df = pd.read_excel('../data/raw/Hbvar thalassemia dataset.xlsx', skiprows=2)
    
    def extract_gene(hgvs):
        if pd.isna(hgvs): return 'Unknown'
        return str(hgvs).split(':')[0].replace("'", "")
        
    df['gene'] = df['hgvs_name'].apply(extract_gene)
    df = df[df['gene'] == 'HBB']
    
    df['mutation'] = df['hgvs_name'].str.replace("'", "")
    df['mutation_class'] = df['type_of_thal'].str.replace("'", "")
    
    def get_severity(mclass):
        mclass = str(mclass).lower()
        if 'beta0' in mclass: return 'Major'
        if 'beta+' in mclass: return 'Intermedia'
        return 'Minor'
        
    df['severity'] = df['mutation_class'].apply(get_severity)
    df['disease_type'] = 'Beta-thalassemia'
    
    # dbSNP id for merge
    df['dbsnp_id'] = df['dbSNP_IDs'].astype(str).str.split(',').str[0]
    
    keep_cols = ['gene', 'mutation', 'severity', 'mutation_class', 'disease_type', 'dbsnp_id']
    df = df[keep_cols]
    
    df.to_csv('../data/cleaned/hbvar_clean.csv', index=False)
    print(f"HbVar cleaned: {len(df)} rows")
    return df

if __name__ == "__main__":
    clean_clinvar()
    clean_gnomad()
    clean_hbvar()
    print("Data cleaning complete.")
