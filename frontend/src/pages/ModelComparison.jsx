import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts';
import { getModelComparison } from '../api';

// ── Design tokens ─────────────────────────────────────────────────────────────
const MODEL_META = {
  'Logistic Regression': { color: '#8b949e', short: 'LR',      icon: '📐' },
  'Random Forest':       { color: '#3fb950', short: 'RF',      icon: '🌲' },
  'XGBoost':             { color: '#58a6ff', short: 'XGB',     icon: '⚡' },
  'LightGBM':            { color: '#d29922', short: 'LGBM',    icon: '💡' },
  'MLP Neural Network':  { color: '#f85149', short: 'MLP',     icon: '🧠' },
};

const RANK_MEDALS  = ['🥇', '🥈', '🥉', '④', '⑤'];
const METRIC_OPTS  = [
  { key: 'roc_auc',   label: 'ROC-AUC'   },
  { key: 'accuracy',  label: 'Accuracy'   },
  { key: 'f1_score',  label: 'F1 Score'   },
  { key: 'precision', label: 'Precision'  },
  { key: 'recall',    label: 'Recall'     },
];

// Helper to safely get metric value
const getMetricVal = (m, key) => {
  if (typeof m[key] === 'number') return m[key];
  if (m[`cv_${key}`] && typeof m[`cv_${key}`].mean === 'number') return m[`cv_${key}`].mean;
  return 0;
};

function colourFor(v) {
  const pct = v * 100;
  return pct >= 75 ? '#3fb950' : pct >= 55 ? '#d29922' : '#f85149';
}

// ── Reusable sub-components ───────────────────────────────────────────────────
function MetricCell({ value }) {
  const col = colourFor(value);
  return (
    <td style={{ padding: '11px 18px', textAlign: 'right', verticalAlign: 'middle' }}>
      <span style={{ color: col, fontWeight: 700, fontFamily: 'monospace', fontSize: '0.95rem' }}>
        {value.toFixed(3)}
      </span>
      <div style={{ height: 3, marginTop: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${value * 100}%`, height: '100%', background: col, borderRadius: 2 }} />
      </div>
    </td>
  );
}

function SectionCard({ title, sub, children, style = {} }) {
  return (
    <div style={{
      background: 'var(--bg-panel)', border: '1px solid var(--border)',
      borderRadius: 12, padding: 24, ...style,
    }}>
      <h3 style={{ margin: '0 0 4px' }}>{title}</h3>
      {sub && <p style={{ margin: '0 0 18px', fontSize: '0.83rem', color: 'var(--text-secondary)' }}>{sub}</p>}
      {children}
    </div>
  );
}

function ROCTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-panel)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem'
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 6 }}>FPR {Number(label).toFixed(2)}</div>
      {payload
        .filter(p => p.dataKey !== 'random')
        .sort((a, b) => b.value - a.value)
        .map(p => (
          <div key={p.dataKey} style={{ color: p.color, marginBottom: 2 }}>
            {p.dataKey}: {Number(p.value).toFixed(3)}
          </div>
        ))}
    </div>
  );
}

// ── Confusion matrix heatmap ──────────────────────────────────────────────────
function ConfusionMatrix({ cm, classes, modelName }) {
  return (
    <div>
      <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: 14 }}>
        Predicted vs actual on {cm.reduce((s, r) => s + r.reduce((a, b) => a + b, 0), 0)} test samples.
        Diagonal = correct predictions.
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr>
              <th style={{ padding: '8px 14px', color: 'var(--text-secondary)', fontSize: '0.75rem', textAlign: 'right' }}>
                Actual ↓&nbsp;/&nbsp;Pred →
              </th>
              {classes.map(c => (
                <th key={c} style={{
                  padding: '8px 14px', textAlign: 'center',
                  color: 'var(--accent)', fontSize: '0.82rem', fontWeight: 600,
                }}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cm.map((row, ri) => {
              const rowSum = row.reduce((a, b) => a + b, 0);
              return (
                <tr key={ri}>
                  <td style={{
                    padding: '10px 14px', fontWeight: 600,
                    color: 'var(--accent)', fontSize: '0.82rem', textAlign: 'right'
                  }}>{classes[ri]}</td>
                  {row.map((val, ci) => {
                    const ratio  = rowSum > 0 ? val / rowSum : 0;
                    const isDiag = ri === ci;
                    return (
                      <td key={ci} style={{
                        padding: '10px 18px', textAlign: 'center', minWidth: 70,
                        border: '1px solid var(--border)',
                        background: isDiag
                          ? `rgba(63,185,80,${0.08 + ratio * 0.55})`
                          : val > 0 ? `rgba(218,54,51,${0.04 + ratio * 0.35})` : 'transparent',
                        color: isDiag ? '#3fb950' : val > 0 ? '#f85149' : 'var(--text-secondary)',
                        fontWeight: isDiag ? 700 : 400,
                        fontFamily: 'monospace',
                      }}>
                        <div>{val}</div>
                        <div style={{ fontSize: '0.7rem', opacity: 0.75 }}>
                          {rowSum > 0 ? `${(ratio * 100).toFixed(0)}%` : '—'}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ModelComparison() {
  const [data,          setData]          = useState(null);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [activeMetric,  setActiveMetric]  = useState('roc_auc');
  const [activeCMModel, setActiveCMModel] = useState(null);

  useEffect(() => {
    getModelComparison()
      .then(d => {
        setData(d);
        setActiveCMModel(d.metrics[0]?.model);
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  // ── Loading / Error states ───────────────────────────────────────────────
  if (loading) return (
    <div style={{ padding: 40, color: 'var(--text-secondary)' }}>⏳ Loading model comparison…</div>
  );
  if (error) return (
    <div style={{ padding: 40 }}>
      <div style={{
        background: 'rgba(218,54,51,0.1)', border: '1px solid #da3633',
        borderRadius: 8, padding: '20px 24px', color: '#f85149',
      }}>
        <strong>⚠ Model data not found</strong>
        <p style={{ marginTop: 8, fontSize: '0.9rem', color: '#8b949e' }}>
          Train all 5 models first:<br />
          <code>python3 models/multi_model_trainer.py</code>
        </p>
        <p style={{ fontSize: '0.8rem', marginTop: 6, color: '#8b949e' }}>{error}</p>
      </div>
    </div>
  );

  if (!data || !data.metrics || data.metrics.length === 0) {
    return (
      <div style={{ padding: 40, color: '#f85149' }}>
        <strong>⚠ Invalid model comparison data received from server.</strong>
        <pre style={{ fontSize: '0.8rem', marginTop: 10 }}>{JSON.stringify(data, null, 2)}</pre>
      </div>
    );
  }

  const { metrics, roc_fpr_grid, roc_curves, classes, n_cv_samples, n_holdout } = data;
  const bestModel = metrics[0] || {};

  // ── Build ROC chart data (merge all models onto shared FPR grid) ─────────
  const rocChartData = roc_fpr_grid
    .map((fpr, i) => {
      const pt = { fpr, random: fpr };
      Object.entries(roc_curves).forEach(([m, info]) => { pt[m] = info.tpr[i]; });
      return pt;
    })
    .filter((_, i) => i % 2 === 0);   // downsample to 50 pts for performance

  // ── Build metric bar chart data ──────────────────────────────────────────
  const barData = metrics.map(m => ({
    name:     MODEL_META[m.model]?.short ?? m.model,
    fullName: m.model,
    value:    getMetricVal(m, activeMetric),
    color:    MODEL_META[m.model]?.color ?? '#8b949e',
  }));

  // ── Active CM model ──────────────────────────────────────────────────────
  const cmModel = metrics.find(m => m.model === activeCMModel) || metrics[0] || {};

  return (
    <div>

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="page-header">
        <h1>Model Comparison Dashboard</h1>
        <p>
          Comparative evaluation of <strong>{metrics.length} ML models</strong> trained on{' '}
          <strong>{((n_cv_samples || 0) + (n_holdout || 0)).toLocaleString()}</strong> labeled HBB variants
          ({(n_cv_samples || 0).toLocaleString()} train / {(n_holdout || 0).toLocaleString()} test).
          &nbsp;Target classes:&nbsp;
          {classes.map((c, i) => (
            <span key={c}>
              <code>{c}</code>{i < classes.length - 1 ? ' · ' : ''}
            </span>
          ))}
        </p>
      </div>

      {/* ── Best model highlight ─────────────────────────────────────────── */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(88,166,255,0.06), rgba(63,185,80,0.06))',
        border: '1px solid rgba(88,166,255,0.25)', borderRadius: 14,
        padding: '22px 28px', marginBottom: 32,
        display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap',
      }}>
        <div style={{ fontSize: '3rem', lineHeight: 1 }}>🏆</div>
        <div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Best Model
          </div>
          <div style={{
            fontSize: '1.5rem', fontWeight: 700,
            color: MODEL_META[bestModel.model]?.color ?? '#58a6ff',
            display: 'flex', alignItems: 'center', gap: 10, marginTop: 2,
          }}>
            {MODEL_META[bestModel.model]?.icon} {bestModel.model}
          </div>
        </div>
        {[
          { l: 'ROC-AUC',  v: getMetricVal(bestModel, 'roc_auc')   },
          { l: 'Accuracy', v: getMetricVal(bestModel, 'accuracy')   },
          { l: 'F1 Score', v: getMetricVal(bestModel, 'f1_score')   },
          { l: 'Precision',v: getMetricVal(bestModel, 'precision')  },
        ].map(({ l, v }) => (
          <div key={l} style={{
            background: 'rgba(0,0,0,0.2)', borderRadius: 10, padding: '10px 20px', textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{l}</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: colourFor(v) }}>{v.toFixed(3)}</div>
          </div>
        ))}
      </div>

      {/* ── Leaderboard table ────────────────────────────────────────────── */}
      <h2 style={{ marginBottom: 14 }}>📊 Model Leaderboard</h2>
      <div className="table-container" style={{ marginBottom: 32 }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: 60 }}>Rank</th>
              <th>Model</th>
              <th style={{ textAlign: 'right' }}>Accuracy</th>
              <th style={{ textAlign: 'right' }}>Precision</th>
              <th style={{ textAlign: 'right' }}>Recall</th>
              <th style={{ textAlign: 'right' }}>F1 Score</th>
              <th style={{ textAlign: 'right' }}>ROC-AUC ⭐</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, idx) => (
              <tr key={m.model} style={{
                background: idx === 0 ? 'rgba(63,185,80,0.05)' : 'transparent',
                transition: 'background 0.15s',
              }}>
                <td style={{ textAlign: 'center', fontSize: '1.25rem', paddingLeft: 16 }}>
                  {RANK_MEDALS[idx] ?? idx + 1}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%',
                      background: MODEL_META[m.model]?.color ?? '#8b949e', flexShrink: 0,
                    }} />
                    <span style={{ fontWeight: idx === 0 ? 700 : 400 }}>
                      {MODEL_META[m.model]?.icon} {m.model}
                    </span>
                  </div>
                </td>
                <MetricCell value={getMetricVal(m, 'accuracy')}  />
                <MetricCell value={getMetricVal(m, 'precision')} />
                <MetricCell value={getMetricVal(m, 'recall')}    />
                <MetricCell value={getMetricVal(m, 'f1_score')}  />
                <MetricCell value={getMetricVal(m, 'roc_auc')}   />
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Charts row: Metric bar + ROC curves ─────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 24, marginBottom: 28 }}>

        {/* Metric bar chart */}
        <SectionCard
          title="Metric Comparison"
          sub={`Comparing all models on the selected metric.`}
        >
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <select
              value={activeMetric}
              onChange={e => setActiveMetric(e.target.value)}
              style={{ width: 'auto', padding: '4px 10px', fontSize: '0.85rem' }}
            >
              {METRIC_OPTS.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={barData} margin={{ left: -20, right: 8, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                angle={-20} textAnchor="end"
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
              />
              <Tooltip
                formatter={v => [`${(v * 100).toFixed(1)}%`, METRIC_OPTS.find(o => o.key === activeMetric)?.label]}
                contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 8 }}
              />
              <ReferenceLine y={0.5} stroke="#8b949e55" strokeDasharray="4 4" />
              <Bar dataKey="value" radius={[5, 5, 0, 0]} isAnimationActive>
                {barData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>

        {/* ROC curves */}
        <SectionCard
          title="ROC Curves — Macro OvR"
          sub="One-vs-Rest macro-averaged ROC curves. Dashed = random classifier baseline."
        >
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
            {Object.entries(roc_curves).map(([m, info]) => (
              <div key={m} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '3px 10px', borderRadius: 20,
                background: 'rgba(0,0,0,0.2)', fontSize: '0.78rem',
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: MODEL_META[m]?.color ?? '#8b949e' }} />
                <span style={{ color: 'var(--text-secondary)' }}>{MODEL_META[m]?.short ?? m}</span>
                <span style={{ color: MODEL_META[m]?.color ?? '#8b949e', fontWeight: 700 }}>
                  {info.auc.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={270}>
            <LineChart data={rocChartData} margin={{ left: -10, right: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="fpr" type="number" domain={[0, 1]}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                tickFormatter={v => v.toFixed(1)}
                label={{ value: 'False Positive Rate', position: 'insideBottomRight', offset: -5, fill: 'var(--text-secondary)', fontSize: 11 }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', offset: 10, fill: 'var(--text-secondary)', fontSize: 11 }}
              />
              <Tooltip content={<ROCTooltip />} />
              {/* Random classifier baseline */}
              <Line
                dataKey="random" name="Random" stroke="#8b949e"
                strokeDasharray="5 5" strokeWidth={1.5}
                dot={false} isAnimationActive={false}
              />
              {Object.keys(roc_curves).map(m => (
                <Line
                  key={m} dataKey={m} name={MODEL_META[m]?.short ?? m}
                  stroke={MODEL_META[m]?.color ?? '#8b949e'}
                  strokeWidth={2.5} dot={false} isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </SectionCard>

      </div>

      {/* ── Confusion Matrix ─────────────────────────────────────────────── */}
      <h2 style={{ marginBottom: 14 }}>🔲 Confusion Matrix</h2>

      {/* Model selector tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {metrics.map((m, idx) => {
          const active = m.model === activeCMModel;
          return (
            <button
              key={m.model}
              onClick={() => setActiveCMModel(m.model)}
              style={{
                display: 'flex', alignItems: 'center', gap: 7,
                padding: '7px 16px', borderRadius: 20, cursor: 'pointer',
                border: active
                  ? `2px solid ${MODEL_META[m.model]?.color ?? '#58a6ff'}`
                  : '1px solid var(--border)',
                background: active ? 'rgba(88,166,255,0.08)' : 'var(--bg-panel)',
                color: active ? (MODEL_META[m.model]?.color ?? '#58a6ff') : 'var(--text-secondary)',
                fontWeight: active ? 700 : 400, fontSize: '0.88rem',
                transition: 'all 0.15s',
              }}
            >
              <span>{MODEL_META[m.model]?.icon}</span>
              <span>{MODEL_META[m.model]?.short ?? m.model}</span>
              <span style={{
                background: active ? (MODEL_META[m.model]?.color ?? '#58a6ff') : 'transparent',
                color: active ? '#fff' : 'var(--text-secondary)',
                fontSize: '0.75rem', padding: '1px 7px', borderRadius: 10,
                border: active ? 'none' : '1px solid var(--border)',
              }}>
                {RANK_MEDALS[idx]}
              </span>
            </button>
          );
        })}
      </div>

      <SectionCard
        title={`${MODEL_META[cmModel.model]?.icon ?? ''} ${cmModel.model}`}
        sub={`AUC ${getMetricVal(cmModel, 'roc_auc').toFixed(3)} · F1 ${getMetricVal(cmModel, 'f1_score').toFixed(3)} · Accuracy ${getMetricVal(cmModel, 'accuracy').toFixed(3)}`}
      >
        <ConfusionMatrix cm={cmModel.confusion_matrix} classes={classes} modelName={cmModel.model} />
      </SectionCard>

    </div>
  );
}
