"""
Genomic Agent for GeneTrustAI-Thal.
Orchestrates the entire VCF → QC → Predict → RAG → LLM pipeline.
"""

from pathlib import Path
import os
from cyvcf2 import VCF
from .retriever import retriever
from .llm import llm_service
from models.severity_model import predict_severity

# Try to import the XGBoost model for pathogenicity
import pickle
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models" / "saved_models"

# ── Load Pathogenicity Model ─────────────────────────────────────────────────
xgb_model = None
encoders = {}
features = []

try:
    with open(MODELS_DIR / "xgboost.pkl", "rb") as f:
        model_data = pickle.load(f)
        xgb_model = model_data["model"]
        encoders = model_data["encoders"]
        features = model_data["features"]
except Exception as e:
    print(f"⚠ Warning: Could not load XGBoost model: {e}")

class GenomicAgent:
    def parse_vcf(self, vcf_path: str):
        """Extract HBB variants from VCF."""
        # HBB is on chr11:5218345-5301941 (GRCh38)
        # We'll just look for chr11 variants in this region or accept anything on 11 for demo
        variants = []
        try:
            vcf = VCF(vcf_path)
            for variant in vcf:
                chrom = str(variant.CHROM).replace('chr', '')
                if chrom == '11': # In a real app, check POS against HBB region
                    # Handle multiple ALTs by just taking the first for simplicity
                    alt = variant.ALT[0] if variant.ALT else ""
                    variants.append({
                        "chr": chrom,
                        "pos": variant.POS,
                        "ref": variant.REF,
                        "alt": alt,
                        "qual": variant.QUAL,
                        "filter": variant.FILTER or "PASS",
                        # Mocking some feature values that would normally come from annotation
                        "allele_freq": 0.0001,
                        "homozygote_count": 0,
                        "mutation_class": "Unknown",
                        "variant_type": "SNP" if len(variant.REF) == len(alt) else "Indel",
                        "zygosity": "Heterozygous" # simplified
                    })
        except Exception as e:
            print(f"VCF Parsing Error: {e}")
            raise ValueError(f"Failed to parse VCF: {e}")
            
        return variants

    def run_qc(self, variants):
        """Basic QC checks."""
        qc_score = 100
        issues = []
        
        if not variants:
            return {"score": 0, "issues": ["No HBB variants found in VCF."]}
            
        for v in variants:
            if v["qual"] is not None and v["qual"] < 20:
                qc_score -= 5
                issues.append(f"Low quality variant at {v['pos']}")
            if v["filter"] != "PASS" and v["filter"] is not None:
                qc_score -= 10
                issues.append(f"Variant failed filter at {v['pos']} ({v['filter']})")
                
        return {
            "score": max(0, qc_score),
            "issues": issues,
            "status": "PASS" if qc_score > 80 else "WARN"
        }

    def predict_variants(self, variants):
        """Run ML models on variants."""
        results = []
        for v in variants:
            # 1. Pathogenicity
            pathogenicity = "Unknown"
            confidence = 0.0
            
            if xgb_model and features:
                try:
                    # Create feature DataFrame
                    # Using dummy values for complex features since this is a demo VCF pipeline
                    # In production, we'd run the full feature engineering pipeline here
                    df_dict = {f: 0 for f in features}
                    df_dict.update({
                        'allele_freq': v['allele_freq'],
                        'homozygote_count': v['homozygote_count'],
                        'mutation_class': v['mutation_class'],
                        'variant_type': v['variant_type']
                    })
                    
                    df = pd.DataFrame([df_dict])
                    
                    # Encode categorical
                    for col in features:
                        if col in encoders and col != 'target':
                            le = encoders[col]
                            known = set(le.classes_)
                            df[col] = df[col].apply(lambda x: x if x in known else 'Missing')
                            mapper = dict(zip(le.classes_, le.transform(le.classes_)))
                            default = mapper.get('Missing', 0)
                            df[col] = df[col].map(lambda x: mapper.get(x, default))
                    
                    X = df[features].copy()
                    pred_idx = xgb_model.predict(X)[0]
                    pred_proba = xgb_model.predict_proba(X)[0]
                    confidence = float(np.max(pred_proba))
                    
                    classes = ['Benign', 'Pathogenic', 'VUS']
                    pathogenicity = classes[pred_idx] if pred_idx < len(classes) else "Unknown"
                except Exception as e:
                    print(f"Prediction error: {e}")
                    
            # 2. Severity
            severity = "Unknown"
            try:
                severity = predict_severity(
                    v['mutation_class'], 
                    v['zygosity'], 
                    "Unknown", 
                    pathogenicity
                )
            except Exception:
                pass
                
            v_res = v.copy()
            v_res["pathogenicity"] = pathogenicity
            v_res["confidence"] = confidence
            v_res["predicted_severity"] = severity
            results.append(v_res)
            
        return results

    def analyze(self, vcf_path: str):
        """Full pipeline execution."""
        # 1. Parse
        variants = self.parse_vcf(vcf_path)
        
        # 2. QC
        qc_data = self.run_qc(variants)
        
        # 3. Predict
        predicted_variants = self.predict_variants(variants)
        
        # 4. Retrieve Knowledge
        # Build a query based on the found variants
        if predicted_variants:
            v = predicted_variants[0]
            query = f"HBB mutation {v['variant_type']} {v['pathogenicity']} {v['predicted_severity']}"
        else:
            query = "Beta-Thalassemia general clinical information"
            
        context = retriever.retrieve_context(query)
        
        # 5. Generate Summary
        summary = llm_service.generate_clinical_summary(predicted_variants, qc_data, context)
        
        return {
            "qc": qc_data,
            "variants": predicted_variants,
            "context_retrieved": bool(context),
            "summary": summary
        }

agent = GenomicAgent()
