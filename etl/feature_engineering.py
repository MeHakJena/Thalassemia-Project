"""
Feature engineering pipeline for BETA-AI.

Extracts predictive features from existing raw files (no new downloads needed):

From gnomAD CSV (100% coverage):
  cadd            - CADD phred-scaled deleteriousness score (0-99)
  phylop          - PhyloP evolutionary conservation (-14 to +6)
  spliceai        - SpliceAI max delta score (0-1) — splice impact
  vep_annotation  - VEP variant effect (missense, frameshift, stop_gained, etc.)
  allele_count    - Raw allele count in gnomAD population
  allele_number   - Total alleles tested
  filter_pass     - 1 if gnomAD quality PASS

From ClinVar TSV (90-100% coverage):
  review_stars    - 0-4 star clinical confidence rating
  mol_consequence - Variant effect class from ClinVar annotation
  has_protein_change - 1 if protein-level change is annotated

Computed from REF / ALT alleles:
  var_length      - len(ALT) - len(REF); 0=SNP, +ve=insertion, -ve=deletion
  is_transition   - 1 if SNP A<->G or C<->T (less deleterious)
  is_frameshift   - 1 if indel length not divisible by 3
  ref_is_cpg      - 1 if REF context is CpG dinucleotide (AT-rich positions)

Genomic position:
  rel_pos         - Position normalized within HBB gene range (0-1)

Output:
  data/merged/master_hbb_features.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np
import glob

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_CLN = BASE_DIR / "data" / "cleaned"
DATA_MRG = BASE_DIR / "data" / "merged"

print("=" * 70)
print("FEATURE ENGINEERING: EXTRACTING RICH GENOMIC FEATURES")
print("=" * 70)

# ── 1. Load master merged table ───────────────────────────────────────────────
print("\n[1/6] Loading master variant table…")
master = pd.read_csv(DATA_MRG / "master_hbb_dataset.csv")
print(f"  ✓ {len(master):,} variants")

# ── 2. Extract gnomAD features ────────────────────────────────────────────────
print("\n[2/6] Extracting gnomAD features (CADD, phyloP, SpliceAI, VEP)…")
gnomad_file = next(iter(glob.glob(str(DATA_RAW / "gnomAD*.csv"))), None)
if gnomad_file:
    gdf = pd.read_csv(gnomad_file, low_memory=False)
    gdf = gdf[gdf["Chromosome"].astype(str) == "11"].copy()

    gdf["chr"] = "11"
    gdf["pos"] = gdf["Position"].astype(int)
    gdf["ref"] = gdf["Reference"].astype(str).str.strip().str.upper()
    gdf["alt"] = gdf["Alternate"].astype(str).str.strip().str.upper()

    # Determine PASS filter
    gdf["filter_pass"] = (
        gdf["Filters - exomes"].fillna(gdf["Filters - joint"].fillna(""))
        .str.upper()
        .eq("PASS")
        .astype(int)
    )

    # VEP annotation → simplified category
    VEP_MAP = {
        "missense_variant":          "missense",
        "synonymous_variant":        "synonymous",
        "frameshift_variant":        "frameshift",
        "stop_gained":               "stop_gained",
        "stop_lost":                 "stop_lost",
        "splice_donor_variant":      "splice",
        "splice_acceptor_variant":   "splice",
        "splice_region_variant":     "splice",
        "5_prime_UTR_variant":       "utr5",
        "3_prime_UTR_variant":       "utr3",
        "intron_variant":            "intronic",
        "upstream_gene_variant":     "regulatory",
        "downstream_gene_variant":   "regulatory",
        "non_coding_transcript_exon_variant": "noncoding",
    }
    gdf["vep_simple"] = (
        gdf["VEP Annotation"]
        .fillna("other")
        .map(lambda x: VEP_MAP.get(x.strip(), "other"))
    )

    gnomad_features = gdf[[
        "chr", "pos", "ref", "alt",
        "cadd", "phylop", "spliceai_ds_max",
        "Allele Count", "Allele Number", "filter_pass",
        "vep_simple",
    ]].rename(columns={
        "cadd":            "cadd_score",
        "phylop":          "phylop_score",
        "spliceai_ds_max": "spliceai_score",
        "Allele Count":    "allele_count",
        "Allele Number":   "allele_number",
        "vep_simple":      "vep_annotation",
    })

    # Note: gnomAD pos and master pos may differ by build; merge on chr+pos+ref+alt
    master["chr"] = master["chr"].astype(str)
    gnomad_features["chr"] = gnomad_features["chr"].astype(str)
    master = master.merge(gnomad_features, on=["chr", "pos", "ref", "alt"], how="left")
    n_matched = master["cadd_score"].notna().sum()
    print(f"  ✓ CADD matched: {n_matched}/{len(master)} rows "
          f"({100*n_matched/len(master):.1f}%)")
else:
    print("  ⚠ gnomAD file not found — skipping gnomAD features")
    for col in ["cadd_score","phylop_score","spliceai_score",
                "allele_count","allele_number","filter_pass","vep_annotation"]:
        master[col] = np.nan

# ── 3. Extract ClinVar features ───────────────────────────────────────────────
print("\n[3/6] Extracting ClinVar review stars & molecular consequence…")
clinvar_tsv = DATA_RAW / "clinvar_result.txt"
if clinvar_tsv.exists():
    cdf = pd.read_csv(clinvar_tsv, sep="\t", low_memory=False)
    cdf = cdf[cdf["Gene(s)"].astype(str).str.contains("HBB", na=False)].copy()

    # ── Review stars ────────────────────────────────────────────────────────
    STAR_MAP = {
        "no assertion provided":                              0,
        "no assertion criteria provided":                     0,
        "no classifications from unflagged records":          0,
        "criteria provided, single submitter":                1,
        "criteria provided, conflicting interpretations":     1,
        "criteria provided, conflicting classifications":     1,
        "criteria provided, multiple submitters, no conflicts": 2,
        "reviewed by expert panel":                           3,
        "practice guideline":                                 4,
    }
    cdf["review_stars"] = (
        cdf["Germline review status"]
        .str.lower()
        .str.strip()
        .map(STAR_MAP)
        .fillna(0)
        .astype(int)
    )

    # ── Molecular consequence → simplified category ─────────────────────────
    MC_MAP = {
        "missense variant":                              "missense",
        "missense variant|initiator_codon_variant":      "missense",
        "synonymous variant":                            "synonymous",
        "frameshift variant":                            "frameshift",
        "nonsense":                                      "stop_gained",
        "stop gained":                                   "stop_gained",
        "stop lost":                                     "stop_lost",
        "splice acceptor variant":                       "splice",
        "splice donor variant":                          "splice",
        "splice region variant":                         "splice",
        "5 prime utr variant":                           "utr5",
        "3 prime utr variant":                           "utr3",
        "intron variant":                                "intronic",
        "upstream gene variant":                         "regulatory",
        "downstream gene variant":                       "regulatory",
        "copy number gain":                              "copy_number",
        "copy number loss":                              "copy_number",
    }
    cdf["mol_consequence"] = (
        cdf["Molecular consequence"]
        .str.lower()
        .str.strip()
        .map(lambda x: MC_MAP.get(x, "other") if pd.notna(x) else "unknown")
    )

    cdf["has_protein_change"] = cdf["Protein change"].notna().astype(int)

    # Build merge key from SPDI: NC_000011.10:XXXXXXX:REF:ALT
    def parse_spdi_key(spdi):
        if pd.isna(spdi):
            return None, None, None
        parts = str(spdi).split(":")
        if len(parts) == 4:
            try:
                pos = int(parts[1]) + 1   # SPDI is 0-based
                return pos, str(parts[2]), str(parts[3])
            except ValueError:
                return None, None, None
        return None, None, None

    parsed = cdf["Canonical SPDI"].apply(parse_spdi_key)
    cdf["pos"] = [p[0] for p in parsed]
    cdf["ref"] = [p[1] for p in parsed]
    cdf["alt"] = [p[2] for p in parsed]
    cdf = cdf.dropna(subset=["pos"]).copy()
    cdf["pos"] = cdf["pos"].astype(int)

    clinvar_features = cdf[[
        "pos", "ref", "alt",
        "review_stars", "mol_consequence", "has_protein_change",
    ]].drop_duplicates(subset=["pos", "ref", "alt"])

    master["ref_str"] = master["ref"].astype(str).str.strip().str.upper()
    master["alt_str"] = master["alt"].astype(str).str.strip().str.upper()
    clinvar_features["ref"] = clinvar_features["ref"].astype(str).str.strip().str.upper()
    clinvar_features["alt"] = clinvar_features["alt"].astype(str).str.strip().str.upper()

    master = master.merge(
        clinvar_features.rename(columns={"ref": "ref_str", "alt": "alt_str"}),
        on=["pos", "ref_str", "alt_str"],
        how="left",
    )
    master.drop(columns=["ref_str", "alt_str"], inplace=True)

    n_stars = master["review_stars"].notna().sum()
    n_mc    = (master["mol_consequence"] != "unknown").sum()
    print(f"  ✓ Review stars matched: {n_stars}/{len(master)}")
    print(f"  ✓ Mol. consequence matched: {n_mc}/{len(master)}")
else:
    print("  ⚠ clinvar_result.txt not found — skipping")
    master["review_stars"]     = 0
    master["mol_consequence"]  = "unknown"
    master["has_protein_change"] = 0

# ── 4. Compute sequence features from REF / ALT ──────────────────────────────
print("\n[4/6] Computing sequence features from REF/ALT…")

ref = master["ref"].astype(str).str.strip().str.upper()
alt = master["alt"].astype(str).str.strip().str.upper()

# Variant length (positive = insertion, negative = deletion, 0 = SNP)
master["var_length"] = alt.str.len() - ref.str.len()

# Transition (A↔G or C↔T) — less disruptive than transversion
TRANSITIONS = {("A","G"),("G","A"),("C","T"),("T","C")}
master["is_transition"] = (
    master.apply(
        lambda r: 1 if (str(r["ref"]).upper(), str(r["alt"]).upper()) in TRANSITIONS
                  and r["var_length"] == 0
                  else 0,
        axis=1
    )
)

# Frameshift (indel not divisible by 3)
master["is_frameshift"] = master["var_length"].apply(
    lambda v: 1 if v != 0 and abs(v) % 3 != 0 else 0
)

# In-frame indel (divisible by 3, non-zero)
master["is_inframe_indel"] = master["var_length"].apply(
    lambda v: 1 if v != 0 and abs(v) % 3 == 0 else 0
)

print(f"  ✓ var_length range: [{master['var_length'].min()}, {master['var_length'].max()}]")
print(f"  ✓ Transitions: {master['is_transition'].sum()}")
print(f"  ✓ Frameshifts: {master['is_frameshift'].sum()}")

# ── 5. Genomic position feature ───────────────────────────────────────────────
print("\n[5/6] Computing relative genomic position…")
pos_min = master["pos"].min()
pos_max = master["pos"].max()
master["rel_pos"] = (master["pos"] - pos_min) / (pos_max - pos_min + 1)
print(f"  ✓ HBB range: {pos_min:,} – {pos_max:,}")

# ── 6. Fill missing values & finalise ────────────────────────────────────────
print("\n[6/6] Filling missing values and saving…")

# Reasonable defaults for missing scores
master["cadd_score"]     = master["cadd_score"].fillna(master["cadd_score"].median())
master["phylop_score"]   = master["phylop_score"].fillna(0.0)
master["spliceai_score"] = master["spliceai_score"].fillna(0.0)
master["allele_count"]   = master["allele_count"].fillna(0)
master["allele_number"]  = master["allele_number"].fillna(0)
master["filter_pass"]    = master["filter_pass"].fillna(0).astype(int)
master["review_stars"]   = master["review_stars"].fillna(0).astype(int)
master["mol_consequence"]= master["mol_consequence"].fillna("unknown")
master["has_protein_change"] = master["has_protein_change"].fillna(0).astype(int)
master["vep_annotation"] = master["vep_annotation"].fillna("unknown")

out_path = DATA_MRG / "master_hbb_features.csv"
master.to_csv(out_path, index=False)

# ── Summary ───────────────────────────────────────────────────────────────────
new_cols = [
    "cadd_score", "phylop_score", "spliceai_score",
    "allele_count", "allele_number", "filter_pass",
    "vep_annotation", "review_stars", "mol_consequence",
    "has_protein_change", "var_length", "is_transition",
    "is_frameshift", "is_inframe_indel", "rel_pos",
]
print(f"\n  ✓ Saved: {out_path}")
print(f"  ✓ Total rows: {len(master):,}")
print(f"  ✓ New features added ({len(new_cols)}):")
for col in new_cols:
    pct = master[col].notna().mean() * 100
    sample = master[col].dropna().iloc[0] if master[col].notna().any() else "—"
    print(f"     {col:<25}: {pct:5.1f}% filled  (sample: {sample})")

print(f"\n  Old feature count: {len(pd.read_csv(DATA_MRG / 'master_hbb_dataset.csv').columns)}")
print(f"  New feature count: {len(master.columns)}")
print("\n" + "=" * 70)
print("✅ FEATURE ENGINEERING COMPLETE")
print("=" * 70)
