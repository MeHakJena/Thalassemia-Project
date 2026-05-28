import React, { useState, useEffect } from 'react';
import { getEdaData } from '../api';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { Loader2, AlertCircle, Activity, BarChart2, PieChart as PieIcon } from 'lucide-react';

const COLORS = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6'];

export default function ExploratoryAnalysis() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getEdaData();
        setData(res);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh', gap: 16 }}>
        <Loader2 size={32} className="spin" color="var(--accent)" />
        <p style={{ color: 'var(--text-secondary)' }}>Crunching Exploratory Data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card fade-in" style={{ borderColor: 'var(--danger)', backgroundColor: 'rgba(239,68,68,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--danger)' }}>
          <AlertCircle size={24} />
          <h3 style={{ margin: 0 }}>Failed to load EDA data</h3>
        </div>
        <p style={{ marginTop: 12 }}>{error}</p>
      </div>
    );
  }

  if (!data) return null;

  // Prepare heatmap data
  const { numerical_columns, correlation_matrix, feature_importance, class_distribution } = data;
  
  const getHeatmapColor = (value) => {
    // Value is between -1 and 1
    // Let's use red for positive, blue for negative
    if (value > 0) {
      return `rgba(239, 68, 68, ${Math.abs(value)})`; // Red
    } else {
      return `rgba(59, 130, 246, ${Math.abs(value)})`; // Blue
    }
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24, paddingBottom: 40 }}>
      <div style={{ padding: '0 8px' }}>
        <h1 style={{ fontSize: '1.8rem', margin: '0 0 8px 0' }}>Exploratory Data Analysis</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '1.1rem' }}>
          Uncover the statistical patterns within the Master HBB Dataset before ML training.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
        
        {/* Class Distribution */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ padding: 8, backgroundColor: 'rgba(59,130,246,0.1)', borderRadius: 8 }}>
              <PieIcon size={20} color="var(--accent)" />
            </div>
            <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Class Distribution</h2>
          </div>
          <div style={{ flex: 1, minHeight: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={class_distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {class_distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', borderRadius: 8 }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Legend verticalAlign="bottom" height={36}/>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feature Importance */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ padding: 8, backgroundColor: 'rgba(59,130,246,0.1)', borderRadius: 8 }}>
              <BarChart2 size={20} color="var(--accent)" />
            </div>
            <h2 style={{ fontSize: '1.2rem', margin: 0 }}>XGBoost Feature Importance</h2>
          </div>
          <div style={{ flex: 1, minHeight: 300 }}>
            {feature_importance.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={feature_importance} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="feature" width={100} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', borderRadius: 8 }}
                    formatter={(value) => value.toFixed(3)}
                  />
                  <Bar dataKey="importance" fill="var(--accent)" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                No feature importance data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Correlation Matrix Heatmap */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{ padding: 8, backgroundColor: 'rgba(59,130,246,0.1)', borderRadius: 8 }}>
            <Activity size={20} color="var(--accent)" />
          </div>
          <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Pearson Correlation Heatmap</h2>
        </div>
        
        <div style={{ overflowX: 'auto', padding: '12px 0' }}>
          {numerical_columns.length > 0 ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: `120px repeat(${numerical_columns.length}, 80px)`,
              gap: 2 
            }}>
              {/* Header row */}
              <div /> 
              {numerical_columns.map(col => (
                <div key={col} style={{ 
                  writingMode: 'vertical-rl', 
                  transform: 'rotate(180deg)', 
                  textAlign: 'left',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  padding: '8px 4px'
                }}>
                  {col}
                </div>
              ))}

              {/* Data rows */}
              {numerical_columns.map(rowCol => (
                <React.Fragment key={rowCol}>
                  <div style={{ 
                    fontSize: '0.8rem', 
                    color: 'var(--text-secondary)', 
                    display: 'flex', 
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: 12
                  }}>
                    {rowCol}
                  </div>
                  {numerical_columns.map(colCol => {
                    const corr = correlation_matrix.find(c => c.x === rowCol && c.y === colCol);
                    const val = corr ? corr.value : 0;
                    return (
                      <div 
                        key={`${rowCol}-${colCol}`}
                        title={`${rowCol} & ${colCol}: ${val}`}
                        style={{
                          backgroundColor: getHeatmapColor(val),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.75rem',
                          color: Math.abs(val) > 0.5 ? 'white' : 'var(--text-primary)',
                          height: 60,
                          borderRadius: 4
                        }}
                      >
                        {val.toFixed(2)}
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 40 }}>
              No numerical columns available for correlation
            </div>
          )}
        </div>
      </div>
      
    </div>
  );
}
