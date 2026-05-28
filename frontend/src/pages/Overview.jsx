import React, { useEffect, useState } from 'react';
import { getDatasetOverview } from '../api';
import { useAppContext } from '../context/AppContext';

// ── Badge colours per pathogenicity class ───────────────────────────────────
const BADGE_COLOR = {
  Pathogenic:        { bg: 'rgba(218,54,51,0.15)', color: '#f85149' },
  Likely_pathogenic: { bg: 'rgba(218,54,51,0.08)', color: '#ffa198' },
  Benign:            { bg: 'rgba(35,134,54,0.15)', color: '#3fb950' },
  Likely_benign:     { bg: 'rgba(35,134,54,0.08)', color: '#56d364' },
  VUS:               { bg: 'rgba(210,153,34,0.15)', color: '#d29922' },
  Other:             { bg: 'rgba(139,148,158,0.15)', color: '#8b949e' },
  Unknown:           { bg: 'rgba(139,148,158,0.10)', color: '#8b949e' },
};

function PathoBadge({ value }) {
  const style = BADGE_COLOR[value] || BADGE_COLOR.Unknown;
  return (
    <span style={{
      ...style,
      padding: '3px 10px',
      borderRadius: '12px',
      fontSize: '0.78rem',
      fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {value || '—'}
    </span>
  );
}

// ── Stats Card ───────────────────────────────────────────────────────────────
function StatCard({ title, value, accent }) {
  return (
    <div className="metric-card" style={accent ? { borderColor: accent } : {}}>
      <div className="metric-title">{title}</div>
      <div className="metric-value" style={accent ? { color: accent } : {}}>{value ?? '—'}</div>
    </div>
  );
}

export default function Overview() {
  const { setPageContext } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setPageContext("The user is on the Overview tab, which is currently loading dataset metrics.");
    getDatasetOverview()
      .then(d => { 
        setData(d); 
        setLoading(false); 
        setPageContext(`The user is on the Overview tab viewing the beta-thalassemia dataset metrics. Data summary: ${d.total_variants} total variants, ${d.labeled_variants} labeled variants. Pathogenicity breakdown: ${d.pathogenic} Pathogenic, ${d.likely_pathogenic} Likely Pathogenic, ${d.vus} VUS, ${d.likely_benign} Likely Benign, ${d.benign} Benign. Genomic range is ${d.genomic_range}.`);
      })
      .catch(err => { 
        setError(err.message); 
        setLoading(false); 
        setPageContext(`The user is on the Overview tab but an error occurred while loading data: ${err.message}`);
      });
  }, [setPageContext]);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 40, color: 'var(--text-secondary)' }}>
      <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
      Loading dataset metrics…
    </div>
  );

  if (error) return (
    <div style={{ padding: 40 }}>
      <div style={{
        background: 'rgba(218,54,51,0.1)', border: '1px solid #da3633',
        borderRadius: 8, padding: '20px 24px', color: '#f85149'
      }}>
        <strong>⚠ Could not connect to the API</strong>
        <p style={{ marginTop: 8, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          Make sure the FastAPI server is running:<br />
          <code style={{ color: '#58a6ff' }}>python3 -m uvicorn api.main:app --reload --port 8000</code>
        </p>
        <p style={{ marginTop: 6, fontSize: '0.8rem', color: '#8b949e' }}>{error}</p>
      </div>
    </div>
  );

  const rows = data.table_data || [];
  const filtered = search
    ? rows.filter(r =>
        Object.values(r).some(v => String(v).toLowerCase().includes(search.toLowerCase()))
      )
    : rows;

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h1>Dataset Overview</h1>
        <p>
          Trusted Beta-Thalassemia HBB variants merged from{' '}
          <strong>ClinVar</strong>, <strong>gnomAD</strong>, and <strong>HbVar</strong>.
          Genomic range: <code style={{ color: 'var(--accent)' }}>{data.genomic_range}</code>
        </p>
      </div>

      {/* Stats */}
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px,1fr))' }}>
        <StatCard title="Total Variants"      value={data.total_variants?.toLocaleString()} />
        <StatCard title="Labeled"             value={data.labeled_variants?.toLocaleString()} />
        <StatCard title="Pathogenic"          value={data.pathogenic?.toLocaleString()}       accent="#f85149" />
        <StatCard title="Likely Pathogenic"   value={data.likely_pathogenic?.toLocaleString()} accent="#ffa198" />
        <StatCard title="VUS"                 value={data.vus?.toLocaleString()}               accent="#d29922" />
        <StatCard title="Likely Benign"       value={data.likely_benign?.toLocaleString()}     accent="#56d364" />
        <StatCard title="Benign"              value={data.benign?.toLocaleString()}             accent="#3fb950" />
      </div>

      {/* Table */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2>Variant Table <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 400 }}>(first 100 rows)</span></h2>
        <input
          placeholder="🔍  Search variants…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: 240 }}
        />
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Gene</th>
              <th>Chr</th>
              <th>Position</th>
              <th>Ref</th>
              <th>Alt</th>
              <th>Pathogenicity</th>
              <th>Type</th>
              <th>Allele Freq</th>
              <th>Hom. Count</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 24 }}>No matching variants</td></tr>
            )}
            {filtered.map((row, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600, color: 'var(--accent)' }}>{row.gene || 'HBB'}</td>
                <td>chr{row.chr}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{Number(row.pos).toLocaleString()}</td>
                <td style={{ fontFamily: 'monospace', color: '#79c0ff' }}>{row.ref}</td>
                <td style={{ fontFamily: 'monospace', color: '#ffa657' }}>{row.alt}</td>
                <td><PathoBadge value={row.pathogenicity} /></td>
                <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{row.variant_type}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>
                  {row.allele_freq !== '' ? Number(row.allele_freq).toExponential(2) : '—'}
                </td>
                <td style={{ textAlign: 'right' }}>{row.homozygote_count !== '' ? row.homozygote_count : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
