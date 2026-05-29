"""
Knowledge Base Builder for BETA-AI.

Indexes multiple sources into ChromaDB for RAG retrieval:
1. Clinical Knowledge (beta_thal_clinical.json)
2. Variant Information (from master_hbb_features.csv)

Requires: chromadb, sentence-transformers, pandas
"""

import os
import json
import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parent.parent
RAG_DIR = BASE_DIR / "rag"
DB_DIR = RAG_DIR / "chroma_db"
KNOWLEDGE_FILE = RAG_DIR / "knowledge" / "beta_thal_clinical.json"
VARIANTS_FILE = BASE_DIR / "data" / "merged" / "master_hbb_features.csv"

print("=" * 70)
print("BUILDING RAG KNOWLEDGE BASE (ChromaDB)")
print("=" * 70)

# Initialize ChromaDB client (persistent on disk)
DB_DIR.mkdir(parents=True, exist_ok=True)
client = chromadb.PersistentClient(path=str(DB_DIR))

# Use SentenceTransformers for local embedding generation (fast, free, good for clinical text)
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create a collection
collection_name = "genetrust_knowledge"
try:
    client.delete_collection(name=collection_name)
    print(f"  Removed existing collection '{collection_name}'")
except Exception:
    pass

collection = client.create_collection(
    name=collection_name, 
    embedding_function=sentence_transformer_ef
)

documents = []
metadatas = []
ids = []

# ── 1. Index Clinical Knowledge JSON ──────────────────────────────────────────
print("\n[1/2] Indexing clinical knowledge base...")
if KNOWLEDGE_FILE.exists():
    with open(KNOWLEDGE_FILE, 'r') as f:
        clinical_data = json.load(f)
    
    for i, item in enumerate(clinical_data):
        doc = f"{item['topic']}:\n{item['content']}"
        documents.append(doc)
        metadatas.append({"source": "clinical_kb", "topic": item['topic']})
        ids.append(f"kb_{i}")
    print(f"  ✓ Added {len(clinical_data)} clinical topics")
else:
    print(f"  ⚠ {KNOWLEDGE_FILE.name} not found")

# ── 2. Index Variant Knowledge (master_hbb_features.csv) ────────────────────
print("\n[2/2] Indexing HBB variant database...")
if VARIANTS_FILE.exists():
    df = pd.read_csv(VARIANTS_FILE)
    # Filter to only variants with a known pathogenicity to keep index focused
    df_known = df[df['pathogenicity'] != 'Unknown'].copy()
    
    # We don't need to index all 2000+ variants if they are very similar.
    # Let's index a representative set or just the most common ones.
    # Actually, indexing all 1929 labeled variants is fine for Chroma.
    
    count = 0
    for _, row in df_known.iterrows():
        # Create a rich text summary of the variant
        hgvs_c = f"c.{row.get('pos', '?')}{row.get('ref', '?')}>{row.get('alt', '?')}"
        doc = (
            f"Variant: HBB {hgvs_c} (chr11:{row.get('pos', '?')})\n"
            f"Type: {row.get('variant_type', 'Unknown')}, Consequence: {row.get('mol_consequence', 'Unknown')}\n"
            f"ClinVar Classification: {row.get('pathogenicity', 'Unknown')}\n"
            f"Review Status: {row.get('review_stars', 0)} stars\n"
            f"gnomAD Allele Frequency: {row.get('allele_freq', 'Unknown')}\n"
            f"CADD Score (Deleteriousness): {row.get('cadd_score', 'Unknown')}\n"
        )
        documents.append(doc)
        metadatas.append({
            "source": "variant_db", 
            "chr": str(row.get('chr', '11')), 
            "pos": str(row.get('pos', '')),
            "ref": str(row.get('ref', '')),
            "alt": str(row.get('alt', '')),
            "pathogenicity": str(row.get('pathogenicity', ''))
        })
        ids.append(f"var_{count}")
        count += 1
    
    print(f"  ✓ Added {count} known HBB variants")
else:
    print(f"  ⚠ {VARIANTS_FILE.name} not found")

# ── 3. Add to ChromaDB ───────────────────────────────────────────────────────
print(f"\nAdding {len(documents)} total documents to vector store...")
# Batch addition to handle limits
batch_size = 5000
for i in range(0, len(documents), batch_size):
    end = min(i + batch_size, len(documents))
    collection.add(
        documents=documents[i:end],
        metadatas=metadatas[i:end],
        ids=ids[i:end]
    )

print(f"  ✓ Successfully indexed to {DB_DIR}")
print("\n" + "=" * 70)
print("✅ KNOWLEDGE BASE BUILT SUCCESSFULLY")
print("=" * 70)
