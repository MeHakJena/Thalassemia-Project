from cyvcf2 import VCF
import pandas as pd
import os

# Create output directory if it doesn't exist
os.makedirs('data/processed', exist_ok=True)

print("Loading ClinVar VCF...")
vcf = VCF("data/raw/clinvar.vcf.gz")

variants = []

for variant in vcf:
    info = variant.INFO

    # Extract gene info
    geneinfo = info.get("GENEINFO", "")

    # Keep only HBB variants
    if geneinfo and "HBB" in geneinfo:
        variants.append({
            "chrom": variant.CHROM,
            "pos": variant.POS,
            "ref": variant.REF,
            "alt": ",".join(variant.ALT),
            "qual": variant.QUAL,
            "filter": variant.FILTER if variant.FILTER else "PASS",
            "geneinfo": geneinfo,
            "clinical_significance": info.get("CLNSIG", ""),
            "variant_id": info.get("ALLELEID", "")
        })

# Convert to DataFrame
df = pd.DataFrame(variants)

# Save CSV
df.to_csv("data/processed/hbb_clinvar_variants.csv", index=False)

print(f"\n✓ Saved: {len(df)} HBB variants")
print(f"✓ Output: data/processed/hbb_clinvar_variants.csv")
print(f"\nFirst few rows:")
print(df.head(10))
print(f"\nData types:\n{df.dtypes}")
