import React, { useState } from 'react';
import { predictSeverity } from '../api';

const SEVERITY_COLORS = {
  Major:    { bg: 'rgba(218,54,51,0.15)',  color: '#f85149', icon: '🔴' },
  Intermedia: { bg: 'rgba(210,153,34,0.15)', color: '#d29922', icon: '🟠' },
  Minor:    { bg: 'rgba(88,166,255,0.12)', color: '#58a6ff', icon: '🔵' },
  Carrier:  { bg: 'rgba(35,134,54,0.12)',  color: '#3fb950', icon: '🟢' },
  Unknown:  { bg: 'rgba(139,148,158,0.1)', color: '#8b949e', icon: '⚪' },
};

const SEVERITY_DESCRIPTIONS = {
  Major:      'Severe phenotype (Thalassemia Major). Requires regular blood transfusions and chelation therapy.',
  Intermedia: 'Moderate phenotype (Thalassemia Intermedia). Variable severity; may require occasional transfusions.',
  Minor:      'Carrier state with mild anaemia. Generally asymptomatic; clinical monitoring recommended.',
  Carrier:    'Silent carrier. No significant clinical symptoms; genetic counselling advised.',
  Unknown:    'Severity could not be determined from the provided inputs.',
};

const MUTATION_CLASSES = ['beta0', 'beta+', 'alpha-2', 'delta+', 'Unknown'];
const ZYGOSITY_OPTIONS = ['Heterozygous', 'Homozygous', 'Compound Heterozygous'];
const HBVAR_SEV_OPTIONS = ['Major', 'Intermedia', 'Minor', 'Carrier', 'Unknown'];
const VARIANT_TYPES = ['Pathogenic', 'Benign', 'single nucleotide variant'];

export default function Severity() {
  const [formData, setFormData] = useState({
    mutation_class: 'beta0',
    zygosity:       'Homozygous',
    hbvar_severity: 'Major',
    variant_type:   'Pathogenic',
  });
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleChange = e =>
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predictSeverity(formData);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const sev = result?.severity;
  const sevStyle = sev ? (SEVERITY_COLORS[sev] || SEVERITY_COLORS.Unknown) : null;

  return (
    <div>
      <div className="page-header">
        <h1>Disease Severity Prediction</h1>
        <p>
          Predict Beta-Thalassemia clinical severity using a rule-based AI engine
          informed by HbVar knowledge base, zygosity, and mutation class.
        </p>
      </div>

      {/* Severity scale legend */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))',
        gap: 12, marginBottom: 30
      }}>
        {Object.entries(SEVERITY_COLORS).filter(([k]) => k !== 'Unknown').map(([sev, style]) => (
          <div key={sev} style={{
            background: style.bg, border: `1px solid ${style.color}33`,
            borderRadius: 8, padding: '10px 14px', textAlign: 'center'
          }}>
            <div style={{ fontSize: '1.3rem' }}>{style.icon}</div>
            <div style={{ fontWeight: 700, color: style.color, marginTop: 4 }}>{sev}</div>
          </div>
        ))}
      </div>

      {/* Form */}
      <div className="form-container">
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Mutation Class</label>
              <select id="sev-mutation-class" name="mutation_class" value={formData.mutation_class} onChange={handleChange}>
                {MUTATION_CLASSES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Zygosity</label>
              <select id="sev-zygosity" name="zygosity" value={formData.zygosity} onChange={handleChange}>
                {ZYGOSITY_OPTIONS.map(z => <option key={z} value={z}>{z}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>HbVar Known Severity</label>
              <select id="sev-hbvar" name="hbvar_severity" value={formData.hbvar_severity} onChange={handleChange}>
                {HBVAR_SEV_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Variant Type</label>
              <select id="sev-variant-type" name="variant_type" value={formData.variant_type} onChange={handleChange}>
                {VARIANT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <button id="predict-severity-btn" type="submit" className="primary-btn" disabled={loading}>
            {loading ? '⏳ Predicting…' : '🩺 Predict Severity'}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: 'rgba(218,54,51,0.1)', border: '1px solid #da3633',
          borderRadius: 8, padding: '14px 20px', color: '#f85149', marginBottom: 20
        }}>
          <strong>⚠ Prediction failed</strong>
          <p style={{ marginTop: 4, fontSize: '0.85rem', color: '#8b949e' }}>{error}</p>
        </div>
      )}

      {/* Result */}
      {sev && (
        <div className="result-card" style={{ borderLeftColor: sevStyle.color, background: sevStyle.bg }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: '2.5rem' }}>{sevStyle.icon}</span>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 2 }}>PREDICTED SEVERITY</div>
              <h3 style={{ color: sevStyle.color, fontSize: '1.6rem', margin: 0 }}>{sev}</h3>
            </div>
          </div>
          <p style={{ marginTop: 16, color: 'var(--text-primary)', lineHeight: 1.6 }}>
            {SEVERITY_DESCRIPTIONS[sev] || SEVERITY_DESCRIPTIONS.Unknown}
          </p>
          <div style={{
            marginTop: 14, padding: '10px 14px',
            background: 'rgba(0,0,0,0.2)', borderRadius: 6, fontSize: '0.82rem',
            color: 'var(--text-secondary)'
          }}>
            ⚠ This prediction is for research purposes only and should not replace clinical judgement.
          </div>
        </div>
      )}
    </div>
  );
}
