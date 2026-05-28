import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Database, Activity, Stethoscope, FileSearch, BarChart2, MessageSquare } from 'lucide-react';
import Overview        from './pages/Overview';
import QCDashboard     from './pages/QCDashboard';
import Interpretation  from './pages/Interpretation';
import Severity        from './pages/Severity';
import ModelComparison from './pages/ModelComparison';
import ChatAssistant   from './pages/ChatAssistant';

function App() {
  return (
    <Router>
      <div className="app-container">

        {/* ── Sidebar ─────────────────────────────────────────────────── */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>🧬 GeneTrustAI-Thal</h2>
            <p>Beta-Thalassemia Variant Dashboard</p>
          </div>

          <nav>
            <NavLink
              to="/"
              end
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <Database size={17} /> Dataset Overview
            </NavLink>

            <NavLink
              to="/qc"
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <Activity size={17} /> QC Dashboard
            </NavLink>

            <NavLink
              to="/interpretation"
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <Stethoscope size={17} /> Variant Interpretation
            </NavLink>

            <NavLink
              to="/severity"
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <FileSearch size={17} /> Severity Prediction
            </NavLink>

            {/* ── New tab ────────────────────────────────────────────── */}
            <NavLink
              to="/models"
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <BarChart2 size={17} /> Model Comparison
            </NavLink>

            <NavLink
              to="/chat"
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
            >
              <MessageSquare size={17} /> AI Assistant
            </NavLink>
          </nav>

          {/* Sidebar footer */}
          <div style={{
            marginTop: 'auto', padding: '16px 20px',
            borderTop: '1px solid var(--border)',
            fontSize: '0.75rem', color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}>
            <div style={{ marginBottom: 4, fontWeight: 600, color: 'var(--accent)' }}>5 ML Models</div>
            <div>LR · RF · XGBoost · LightGBM · MLP</div>
            <div style={{ marginTop: 4, opacity: 0.7 }}>API: localhost:8000</div>
          </div>
        </aside>

        {/* ── Main content ─────────────────────────────────────────────── */}
        <main className="main-content">
          <Routes>
            <Route path="/"              element={<Overview        />} />
            <Route path="/qc"            element={<QCDashboard     />} />
            <Route path="/interpretation"element={<Interpretation  />} />
            <Route path="/severity"      element={<Severity        />} />
            <Route path="/models"        element={<ModelComparison />} />
            <Route path="/chat"          element={<ChatAssistant   />} />
          </Routes>
        </main>

      </div>
    </Router>
  );
}

export default App;
