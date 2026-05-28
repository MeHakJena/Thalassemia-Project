import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { predictPathogenicity } from '../api';

// ── Pathogenicity colour map ─────────────────────────────────────────────────
const PATHO_COLOR = {
  Pathogenic:        '#f85149',
  Likely_pathogenic: '#ffa198',
  Benign:            '#3fb950',
  Likely_benign:     '#56d364',
  VUS:               '#d29922',
  Other:             '#8b949e',
};

const MUTATION_CLASSES = ['Unknown', 'beta0', 'beta+', 'alpha-2', 'delta+', 'silent'];
const VARIANT_TYPES    = ['single nucleotide variant', 'Deletion', 'Duplication', 'Indel', 'SNP'];

// ── Confidence bar ────────────────────────────────────────────────────────────
function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100);
  const col = pct >= 70 ? '#3fb950' : pct >= 40 ? '#d29922' : '#f85149';
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Model confidence</span>
        <span style={{ fontWeight: 700, color: col }}>{pct}%</span>
      </div>
      <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: col, borderRadius: 3, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

// ── Custom tooltip for SHAP chart ────────────────────────────────────────────
function SHAPTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: 'var(--bg-panel)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 14px', fontSize: '0.85rem'
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.name}</div>
      <div style={{ color: d.value > 0 ? '#f85149' : '#58a6ff' }}>
        SHAP: {d.value > 0 ? '+' : ''}{d.value.toFixed(4)}
      </div>
    </div>
  );
}

export default function Interpretation() {
  const [formData, setFormData] = useState({
    allele_freq:       0.0001,
    homozygote_count:  0,
    variant_type:      'single nucleotide variant',
    mutation_class:    'Unknown',
  });
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleChange = e => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'allele_freq'       ? parseFloat(value)
             : name === 'homozygote_count' ? parseInt(value, 10)
             : value,
    }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predictPathogenicity(formData);
      // Build SHAP chart data
      const rawValues = Array.isArray(data.shap_values?.[0])
        ? data.shap_values[0]
        : data.shap_values;
      const chartData = (data.features || []).map((feat, i) => ({
        name:  feat,
        value: rawValues?.[i] ?? 0,
      }));
      setResult({ ...data, chartData });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resultColor = result ? PATHO_COLOR[result.prediction] || '#8b949e' : '#58a6ff';

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h1>Variant Interpretation</h1>
        <div style={{ maxWidth: '800px', marginBottom: '20px' }}>
          <p style={{ marginBottom: '12px' }}>
            <strong>What is it?</strong> Variant Interpretation is the process of analyzing a specific genetic mutation (variant) to determine if it is the cause of a disease. In this application, we focus on Beta-Thalassemia variants (HBB gene).
          </p>
          <p style={{ marginBottom: '12px' }}>
            <strong>How does it work?</strong> You input specific clinical characteristics of a variant, such as how common it is in the general population (Allele Frequency) and its mutation type. Our AI model—trained on 1,929 real, clinically validated genomic records from databases like ClinVar and gnomAD—then analyzes these features.
          </p>
          <p>
            The model outputs a <strong>Pathogenicity Prediction</strong> (e.g., Benign, Pathogenic) indicating how likely the variant is to cause Beta-Thalassemia. It also generates a SHAP feature importance graph, explaining exactly <em>why</em> it made that prediction by showing which inputs influenced the result the most.
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="form-container">
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Allele Frequency (gnomAD)</label>
              <input
                id="allele_freq"
                type="number" step="0.000001" min="0" max="1"
                name="allele_freq" value={formData.allele_freq}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label>Homozygote Count</label>
              <input
                id="homozygote_count"
                type="number" min="0"
                name="homozygote_count" value={formData.homozygote_count}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label>Variant Type</label>
              <select id="variant_type" name="variant_type" value={formData.variant_type} onChange={handleChange}>
                {VARIANT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Mutation Class</label>
              <select id="mutation_class" name="mutation_class" value={formData.mutation_class} onChange={handleChange}>
                {MUTATION_CLASSES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <button id="predict-btn" type="submit" className="primary-btn" disabled={loading}>
            {loading ? '⏳ Predicting…' : '🔬 Predict Pathogenicity'}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: 'rgba(218,54,51,0.1)', border: '1px solid #da3633',
          borderRadius: 8, padding: '14px 20px', color: '#f85149', marginBottom: 24
        }}>
          <strong>⚠ Prediction failed</strong>
          <p style={{ marginTop: 4, fontSize: '0.85rem', color: '#8b949e' }}>{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <>
          <div className="result-card" style={{ borderLeftColor: resultColor }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 4 }}>PREDICTION</div>
                <h3 style={{ color: resultColor, fontSize: '1.5rem', margin: 0 }}>{result.prediction}</h3>
              </div>
              <div style={{ flex: 1, minWidth: 200 }}>
                <ConfidenceBar value={result.confidence} />
              </div>
            </div>
            {result.model_classes && (
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {result.model_classes.map(cls => (
                  <span key={cls} style={{
                    padding: '2px 10px', borderRadius: 12, fontSize: '0.78rem',
                    background: cls === result.prediction ? PATHO_COLOR[cls] : 'rgba(139,148,158,0.12)',
                    color: cls === result.prediction ? '#fff' : 'var(--text-secondary)',
                    fontWeight: cls === result.prediction ? 700 : 400,
                  }}>{cls}</span>
                ))}
              </div>
            )}
          </div>

          {/* SHAP chart */}
          <div className="chart-container">
            <h3 style={{ marginBottom: 4 }}>SHAP Feature Importance</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 20 }}>
              <span style={{ color: '#f85149' }}>■ Red</span> features push toward Pathogenic.{' '}
              <span style={{ color: '#58a6ff' }}>■ Blue</span> features push toward Benign/VUS.
            </p>
            <ResponsiveContainer width="100%" height="75%">
              <BarChart
                data={result.chartData}
                layout="vertical"
                margin={{ top: 0, right: 40, left: 120, bottom: 0 }}
              >
                <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-primary)', fontSize: 13 }} width={115} />
                <Tooltip content={<SHAPTooltip />} />
                <ReferenceLine x={0} stroke="var(--border)" />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive>
                  {result.chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.value > 0 ? '#f85149' : '#58a6ff'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
