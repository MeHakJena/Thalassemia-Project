import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Database, Activity, Stethoscope, FileSearch, BarChart2, MessageSquare } from 'lucide-react';
import Overview        from './pages/Overview';
import QCDashboard     from './pages/QCDashboard';
import Interpretation  from './pages/Interpretation';
import Severity        from './pages/Severity';
import ModelComparison from './pages/ModelComparison';
import ChatAssistant   from './pages/ChatAssistant';
import ExploratoryAnalysis from './pages/ExploratoryAnalysis';
import FloatingChat    from './components/FloatingChat';

function App() {
  return (
    <Router>
      <div className="app-container">
        
        {/* ── Top Navigation Bar ────────────────────────────────────────── */}
        <header className="top-nav-bar">
          <div className="top-nav-content">
            <div className="logo-section">
              <h2>🧬 GeneTrustAI-Thal</h2>
              <span className="badge">Beta-Thalassemia AI</span>
            </div>

            <nav className="nav-tabs">
              <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Database size={16} /> <span className="nav-text">Overview</span>
              </NavLink>

              <NavLink to="/qc" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Activity size={16} /> <span className="nav-text">QC</span>
              </NavLink>

              <NavLink to="/eda" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <BarChart2 size={16} /> <span className="nav-text">EDA</span>
              </NavLink>

              <NavLink to="/interpretation" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Stethoscope size={16} /> <span className="nav-text">Interpretation</span>
              </NavLink>

              <NavLink to="/severity" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <FileSearch size={16} /> <span className="nav-text">Severity</span>
              </NavLink>

              <NavLink to="/models" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <BarChart2 size={16} /> <span className="nav-text">Models</span>
              </NavLink>

              <NavLink to="/chat" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <MessageSquare size={16} /> <span className="nav-text">Agent</span>
              </NavLink>
            </nav>
            
            <div className="nav-footer">
              <span className="api-status">API: Online</span>
            </div>
          </div>
        </header>

        {/* ── Main content ─────────────────────────────────────────────── */}
        <main className="main-content">
          <Routes>
            <Route path="/"              element={<Overview        />} />
            <Route path="/qc"            element={<QCDashboard     />} />
            <Route path="/eda"           element={<ExploratoryAnalysis />} />
            <Route path="/interpretation"element={<Interpretation  />} />
            <Route path="/severity"      element={<Severity        />} />
            <Route path="/models"        element={<ModelComparison />} />
            <Route path="/chat"          element={<ChatAssistant   />} />
          </Routes>
        </main>

      </div>
      <FloatingChat />
    </Router>
  );
}

export default App;
