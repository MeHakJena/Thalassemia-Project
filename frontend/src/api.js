/**
 * Centralised API service layer for GeneTrustAI-Thal.
 *
 * All HTTP calls go through here.  To point the frontend at a different
 * backend (staging, cloud, etc.) simply change VITE_API_BASE_URL in .env —
 * no React component changes required.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ─── helpers ────────────────────────────────────────────────────────────────

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${detail}`);
  }
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${detail}`);
  }
  return res.json();
}

// ─── public API ─────────────────────────────────────────────────────────────

/** Health check / service info */
export const getHealth = () => get('/');

/** Dataset overview statistics + first 100 variant rows */
export const getDatasetOverview = () => get('/dataset_overview');

/** QC pipeline statistics (ingestion → repair → trusted) */
export const getQCDashboard = () => get('/qc_dashboard');

/**
 * Predict pathogenicity for a single variant.
 * @param {{ allele_freq: number, homozygote_count: number, variant_type: string, mutation_class: string }} payload
 */
export const predictPathogenicity = (payload) => post('/predict_pathogenicity', payload);

/**
 * Predict clinical severity for a single variant.
 * @param {{ mutation_class: string, zygosity: string, hbvar_severity: string, variant_type: string }} payload
 */
export const predictSeverity = (payload) => post('/predict_severity', payload);

/**
 * Fetch multi-model comparison metrics and ROC curve data.
 * Requires models/multi_model_trainer.py to have been run first.
 */
export const getModelComparison = () => get('/model_comparison');
