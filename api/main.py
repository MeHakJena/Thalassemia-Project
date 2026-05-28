from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from pathlib import Path
import pandas as pd
import pickle
import json
import sys
import os
import numpy as np

# ── Absolute project root (one level above api/) ──────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Add project root to sys.path so model imports work from any CWD
sys.path.insert(0, str(BASE_DIR))
from models.explainability import generate_shap_explanation
from models.severity_model import predict_severity as get_severity
from rag.genomic_agent import agent as genomic_agent
from rag.llm import llm_service
from rag.retriever import get_retriever

app = FastAPI(
    title="GeneTrustAI-Thal API",
    description="AI-powered Beta-Thalassemia variant pathogenicity and severity prediction",
    version="2.0"
)

# Add CORS middleware to allow React app to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PathogenicityRequest(BaseModel):
    """Pathogenicity prediction request"""
    allele_freq: float = 0.0
    homozygote_count: int = 0
    variant_type: str = "SNP"
    mutation_class: str = "Unknown"

class SeverityRequest(BaseModel):
    """Severity prediction request"""
    mutation_class: str
    zygosity: str
    hbvar_severity: str
    variant_type: str

class PredictionResponse(BaseModel):
    """API response for predictions"""
    prediction: str
    confidence: float
    shap_base_value: float
    shap_values: list
    features: list

# ── Load pathogenicity model (absolute path, works from any CWD) ─────────
try:
    MODEL_PATH = BASE_DIR / 'models' / 'saved_models' / 'pathogenicity_model.pkl'
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    xgb_model = model_data['model']
    encoders = model_data['encoders']
    features = model_data['features']
    print(f"✓ Loaded model from {MODEL_PATH}")
    print("✓ Loaded real genomic model (trained on 1,929 HBB variants)")
except Exception as e:
    print(f"⚠ Error loading model: {e}")
    raise

@app.get("/", tags=["Health"])
def read_root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "GeneTrustAI-Thal API",
        "version": "2.0",
        "model": "XGBoost (real genomic data)",
        "training_data": "1,929 HBB variants from ClinVar+gnomAD+HbVar"
    }

@app.get("/dataset_overview", tags=["Dashboard"])
def get_dataset_overview():
    """Get dataset statistics from master variant table"""
    try:
        df = pd.read_csv(BASE_DIR / 'data' / 'merged' / 'master_hbb_dataset.csv')

        # Normalise: add a human-readable 'gene' column (all records are HBB)
        df['gene'] = 'HBB'

        pathogenic_count = int((df['pathogenicity'] == 'Pathogenic').sum())
        benign_count     = int((df['pathogenicity'] == 'Benign').sum())
        vus_count        = int((df['pathogenicity'] == 'VUS').sum())

        # Select the columns the frontend table expects
        table_cols = ['gene', 'chr', 'pos', 'ref', 'alt', 'pathogenicity', 'variant_type',
                      'allele_freq', 'homozygote_count', 'mutation_class']
        available_cols = [c for c in table_cols if c in df.columns]
        table_df = df[available_cols].head(100).fillna("")

        return {
            "total_variants": len(df),
            "labeled_variants": int((df['pathogenicity'] != 'Unknown').sum()),
            "pathogenic": pathogenic_count,
            "benign": benign_count,
            "vus": vus_count,
            "likely_pathogenic": int((df['pathogenicity'] == 'Likely_pathogenic').sum()),
            "likely_benign": int((df['pathogenicity'] == 'Likely_benign').sum()),
            "genomic_range": f"chr11:{int(df['pos'].min()):,}-{int(df['pos'].max()):,}",
            "table_data": table_df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dataset: {str(e)}")

@app.get("/qc_dashboard", tags=["Dashboard"])
def get_qc_dashboard():
    """Return QC pipeline statistics and anomaly samples"""
    try:
        trusted   = pd.read_csv(BASE_DIR / 'data' / 'merged' / 'trusted_variants.csv')
        corrupted = pd.read_csv(BASE_DIR / 'data' / 'merged' / 'synthetic_corrupted_vcf.csv')

        initial_rows = len(corrupted)
        final_rows   = len(trusted)
        dup_key_cols = [c for c in ['chr', 'pos', 'ref', 'alt', 'gene'] if c in corrupted.columns]
        duplicates_removed = initial_rows - len(corrupted.drop_duplicates(subset=dup_key_cols))

        return {
            "ingested_rows": initial_rows,
            "duplicates_repaired": int(duplicates_removed),
            "trusted_output_rows": final_rows,
            "anomalies_sample": corrupted.head(10).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QC data error: {str(e)}")
@app.get("/model_comparison", tags=["Models"])
def get_model_comparison():
    """Return multi-model performance metrics, ROC curve data, and confusion matrices."""
    try:
        comparison_path = BASE_DIR / 'models' / 'saved_models' / 'model_comparison.json'
        with open(comparison_path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Model comparison data not found. Run: python3 models/multi_model_trainer.py"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict_pathogenicity", tags=["Predictions"])
def predict_pathogenicity(req: PathogenicityRequest):
    """
    Predict pathogenicity for a Beta-Thalassemia variant
    
    Returns:
    - prediction: Pathogenic, Benign, VUS, Likely_pathogenic, Likely_benign, or Other
    - confidence: Model confidence (0-1)
    - SHAP values for model explainability
    """
    try:
        # Create dataframe with features in correct order
        df = pd.DataFrame([{
            'allele_freq': req.allele_freq,
            'homozygote_count': req.homozygote_count,
            'mutation_class': req.mutation_class,
            'variant_type': req.variant_type
        }])
        
        # Select and reorder features to match model training
        X = df[features].copy()
        
        # Encode categorical features
        for col in features:
            if col in encoders and col != 'target':
                le = encoders[col]
                known = set(le.classes_)
                X[col] = X[col].apply(lambda x: x if x in known else 'Missing')
                mapper = dict(zip(le.classes_, le.transform(le.classes_)))
                default = mapper.get('Missing', 0)
                X[col] = X[col].map(lambda x: mapper.get(x, default))
        
        # Predict with probabilities
        pred_idx = xgb_model.predict(X)[0]
        pred_proba = xgb_model.predict_proba(X)[0]
        confidence = float(np.max(pred_proba))
        
        target_le = encoders['target']
        prediction = target_le.inverse_transform([pred_idx])[0]
        
        # Try to get SHAP explanation, but don't fail if it errors
        try:
            shap_data = generate_shap_explanation(str(MODEL_PATH), df)
            shap_base_value = shap_data.get('base_value', 0.0)
            shap_values = shap_data.get('values', [])
            shap_features = shap_data.get('features', features)
        except Exception as shap_err:
            print(f"Warning: SHAP generation failed: {shap_err}")
            shap_base_value = 0.0
            shap_values = [0.0] * len(features)
            shap_features = features
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "shap_base_value": shap_base_value,
            "shap_values": shap_values,
            "features": shap_features,
            "model_classes": list(target_le.classes_)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction error: {str(e)}")

@app.post("/predict_severity", tags=["Predictions"])
def predict_severity(req: SeverityRequest):
    """Predict clinical severity (Carrier, Minor, Intermedia, Major)"""
    try:
        sev = get_severity(req.mutation_class, req.zygosity, req.hbvar_severity, req.variant_type)
        return {"severity": sev}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Severity prediction error: {str(e)}")

# ── RAG Chatbot Endpoints ────────────────────────────────────────────────────

@app.post("/analyze_vcf", tags=["RAG Assistant"])
async def analyze_vcf(file: UploadFile = File(...), model_name: str = Form("xgboost")):
    """Upload a VCF file for full agentic analysis (QC -> Predict -> RAG -> Summarize)"""
    # Save the uploaded file temporarily
    temp_path = BASE_DIR / "data" / "temp_upload.vcf"
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
            
        # Run agent with selected model
        result = genomic_agent.analyze(str(temp_path), model_name=model_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()

class ChatRequest(BaseModel):
    message: str
    context: str
    history: List[Dict] = []

@app.post("/chat", tags=["RAG Assistant"])
def chat(req: ChatRequest):
    """Ask follow-up questions to the LLM"""
    try:
        # 1. Get the screen text sent by the frontend
        screen_context = req.context
        
        # 2. Automatically query the local Vector DB (ChromaDB) for clinical knowledge
        retriever = get_retriever()
        kb_context = retriever.retrieve_context(req.message, n_results=3)
        
        # 3. Combine them so the AI knows what's on the screen AND the clinical facts
        combined_context = (
            f"--- SCREEN CONTENT (What the user is looking at) ---\n{screen_context}\n\n"
            f"--- CLINICAL KNOWLEDGE BASE (Vector DB) ---\n{kb_context}\n"
        )
        
        answer = llm_service.answer_question(req.message, combined_context, req.history)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

from fastapi.responses import FileResponse

@app.get("/sample_vcf", tags=["RAG Assistant"])
def get_sample_vcf():
    """Download the sample VCF for testing the pipeline"""
    sample_path = BASE_DIR / "data" / "sample_patient.vcf"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample VCF not found.")
    return FileResponse(
        path=sample_path, 
        filename="sample_patient.vcf", 
        media_type="text/vcard"
    )
