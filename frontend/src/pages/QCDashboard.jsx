import React, { useEffect, useState } from 'react';
import { getQCDashboard } from '../api';

function MetricCard({ title, value, sub, accent }) {
  return (
    <div className="metric-card" style={accent ? { borderColor: accent } : {}}>
      <div className="metric-title">{title}</div>
      <div className="metric-value" style={accent ? { color: accent } : {}}>{value ?? '—'}</div>
      {sub && <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function QCDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getQCDashboard()
      .then(d => { setData(d); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return (
    <div style={{ padding: 40, color: 'var(--text-secondary)' }}>⏳ Loading QC metrics…</div>
  );

  if (error) return (
    <div style={{ padding: 40 }}>
      <div style={{
        background: 'rgba(218,54,51,0.1)', border: '1px solid #da3633',
        borderRadius: 8, padding: '20px 24px', color: '#f85149'
      }}>
        <strong>⚠ API unavailable</strong>
        <p style={{ marginTop: 8, fontSize: '0.85rem', color: '#8b949e' }}>{error}</p>
      </div>
    </div>
  );

  const reductionPct = data.ingested_rows
    ? (((data.ingested_rows - data.trusted_output_rows) / data.ingested_rows) * 100).toFixed(1)
    : 0;

  return (
    <div>
      <div className="page-header">
        <h1>Self-Healing QC Dashboard</h1>
        <p>
          Automated data quality pipeline using{' '}
          <strong>Isolation Forest</strong> anomaly detection — deduplication,
          chromosome normalisation, outlier clamping, and imputation.
        </p>
      </div>

      {/* Stats row */}
      <div className="metrics-grid">
        <MetricCard
          title="Ingested Rows"
          value={data.ingested_rows?.toLocaleString()}
          sub="Raw (corrupted) input"
        />
        <MetricCard
          title="Duplicates Repaired"
          value={data.duplicates_repaired?.toLocaleString()}
          accent="#d29922"
          sub="Identical coordinate records"
        />
        <MetricCard
          title="Trusted Output Rows"
          value={data.trusted_output_rows?.toLocaleString()}
          accent="#3fb950"
          sub={`${reductionPct}% reduction after QC`}
        />
      </div>

      {/* Pipeline steps */}
      <h2 style={{ marginBottom: 16 }}>Pipeline Steps</h2>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))',
        gap: 16, marginBottom: 32
      }}>
        {[
          { icon: '📥', title: 'Ingest',      desc: 'Load raw VCF / CSV records, accept even malformed files.' },
          { icon: '🔍', title: 'Detect',      desc: 'Isolation Forest flags outliers (allele_freq, homozygote_count).' },
          { icon: '🔧', title: 'Repair',      desc: 'Dedup, chr normalise, clip outliers, impute missing values.' },
          { icon: '✅', title: 'Trust',       desc: 'Write clean, validated records to trusted_variants.csv.' },
        ].map(s => (
          <div key={s.title} style={{
            background: 'var(--bg-panel)', border: '1px solid var(--border)',
            borderRadius: 10, padding: '20px 24px'
          }}>
            <div style={{ fontSize: '1.6rem', marginBottom: 8 }}>{s.icon}</div>
            <div style={{ fontWeight: 600, color: 'var(--accent)', marginBottom: 6 }}>{s.title}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{s.desc}</div>
          </div>
        ))}
      </div>

      {/* Anomaly sample table */}
      <h2 style={{ marginBottom: 8 }}>Anomalies Sample</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 16 }}>
        Rows identified as malformed or extreme outliers (highlighted in red).
      </p>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Gene</th>
              <th>Chr</th>
              <th>Pos</th>
              <th>Ref</th>
              <th>Alt</th>
              <th>Allele Freq</th>
              <th>Hom. Count</th>
            </tr>
          </thead>
          <tbody>
            {(data.anomalies_sample || []).map((row, idx) => {
              const badChr  = String(row.chr).startsWith('chr');
              const badFreq = Number(row.allele_freq) > 1;
              const badHom  = Number(row.homozygote_count) < 0;
              return (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: 'var(--accent)' }}>{row.gene || 'HBB'}</td>
                  <td style={{ color: badChr ? 'var(--danger)' : 'inherit', fontWeight: badChr ? 700 : 400 }}>
                    {row.chr}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{Number(row.pos)?.toLocaleString()}</td>
                  <td style={{ fontFamily: 'monospace', color: '#79c0ff' }}>{row.ref}</td>
                  <td style={{ fontFamily: 'monospace', color: '#ffa657' }}>{row.alt}</td>
                  <td style={{ color: badFreq ? 'var(--danger)' : 'inherit', fontWeight: badFreq ? 700 : 400 }}>
                    {row.allele_freq !== '' ? row.allele_freq : '—'}
                  </td>
                  <td style={{ color: badHom ? 'var(--danger)' : 'inherit', fontWeight: badHom ? 700 : 400 }}>
                    {row.homozygote_count !== '' ? row.homozygote_count : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
