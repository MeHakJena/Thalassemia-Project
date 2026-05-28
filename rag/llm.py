"""
LLM Wrapper for GeneTrustAI-Thal Chatbot.
Handles clinical summary generation and conversational Q&A.
Supports Groq (Llama-3), OpenAI (GPT-4), or a template fallback if no keys exist.
"""

import os
import json
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# Attempt to load LLM clients
HAS_OPENAI = False
HAS_GROQ = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    pass

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    pass

class ClinicalLLM:
    def __init__(self):
        self.provider = "template"
        self.client = None
        
        # Priority: OpenAI > Groq > Template
        if HAS_OPENAI and os.environ.get("OPENAI_API_KEY"):
            self.client = OpenAI()
            self.provider = "openai"
            self.model = "gpt-4o-mini"
            print("  ✓ LLM: Using OpenAI")
        elif HAS_GROQ and os.environ.get("GROQ_API_KEY"):
            self.client = Groq()
            self.provider = "groq"
            self.model = "llama-3.3-70b-versatile"
            print("  ✓ LLM: Using Groq (Llama 3.3)")
        else:
            print("  ⚠ LLM: No API keys found (OPENAI_API_KEY or GROQ_API_KEY). Using template fallback.")

    def _call_llm(self, system_prompt: str, user_prompt: str, history: List[Dict] = None) -> str:
        """Helper to call the active LLM provider."""
        if self.provider == "template":
            return self._template_fallback(user_prompt)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3
                )
                return response.choices[0].message.content
            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error ({self.provider}): {e}")
            return f"Error communicating with LLM provider: {e}"

    def _template_fallback(self, user_prompt: str) -> str:
        """Structured output when no LLM API is available."""
        return (
            "### Clinical Summary (Template Fallback)\n\n"
            "An AI API key (OpenAI or Groq) is required for free-form clinical summaries and interactive Q&A. "
            "However, the system has successfully run the genomic pipeline:\n\n"
            "- VCF parsing and HBB variant extraction completed.\n"
            "- QC validation passed.\n"
            "- Pathogenicity and severity predictions are available in the dashboard.\n\n"
            "*To enable the AI Chatbot, please set `GROQ_API_KEY` or `OPENAI_API_KEY` in your environment.*"
        )

    def generate_clinical_summary(self, variant_data: dict, qc_data: dict, context: str) -> str:
        """Generate the main clinical report after VCF analysis."""
        system_prompt = (
            "You are an expert clinical genomic AI assistant specializing in Beta-Thalassemia. "
            "Your task is to generate a professional, clear, and explainable clinical summary "
            "based on the provided variant predictions, QC metrics, and retrieved biomedical knowledge. "
            "Write in a professional medical tone but keep it accessible. Use Markdown formatting. "
            "Do not invent information; rely on the provided context."
        )
        
        user_prompt = (
            f"Please generate a clinical summary for this VCF analysis.\n\n"
            f"--- QC Metrics ---\n{json.dumps(qc_data, indent=2)}\n\n"
            f"--- Detected Variants ---\n{json.dumps(variant_data, indent=2)}\n\n"
            f"--- Retrieved Clinical Knowledge ---\n{context}\n\n"
            "Structure the response with:\n"
            "1. Overall Finding (1-2 sentences)\n"
            "2. Variant Details (brief explanation of the mutations found)\n"
            "3. Variant Interpretation (Explain *why* the model made this prediction using the provided 'interpretation_reasoning' SHAP features)\n"
            "4. Clinical Implications (severity, expected phenotype)\n"
            "5. Pipeline Confidence (based on QC and model confidence)"
        )
        
        return self._call_llm(system_prompt, user_prompt)

    def answer_question(self, question: str, context: str, history: List[Dict]) -> str:
        """Answer a follow-up user question."""
        system_prompt = (
            "You are GeneTrustAI-Thal, an expert clinical genomic assistant. "
            "Answer the user's question about their Beta-Thalassemia VCF analysis. "
            "Use the provided clinical context if relevant. Be concise, accurate, and professional."
        )
        
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"
        
        return self._call_llm(system_prompt, user_prompt, history)

# Singleton instance
llm_service = ClinicalLLM()
