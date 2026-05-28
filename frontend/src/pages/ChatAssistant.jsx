import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, Bot, User, CheckCircle, Clock, FileText, Send, Loader2, Download } from 'lucide-react';
import { analyzeVcf, chat, getSampleVcfUrl } from '../api';
import ReactMarkdown from 'react-markdown';

export default function ChatAssistant() {
  const [file, setFile] = useState(null);
  const [selectedModel, setSelectedModel] = useState('xgboost');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I am GeneTrustAI, your clinical genomic assistant. Please upload a patient VCF file to begin analysis.'
    }
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped && (dropped.name.endsWith('.vcf') || dropped.name.endsWith('.vcf.gz'))) {
      setFile(dropped);
    } else {
      alert('Please drop a valid .vcf file');
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const startAnalysis = async () => {
    if (!file) return;
    
    setAnalyzing(true);
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: `Analyze VCF: ${file.name}`
    }]);

    try {
      const result = await analyzeVcf(file, selectedModel);
      setAnalysisResult(result);
      
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: result.summary,
        isClinicalReport: true,
        qc: result.qc,
        variants: result.variants
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: `Error during analysis: ${err.message}`
      }]);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    
    const userMsg = input.trim();
    setInput('');
    setSending(true);
    
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: userMsg
    }]);

    try {
      // Build context from analysis result if available
      const context = analysisResult 
        ? JSON.stringify({ variants: analysisResult.variants, qc: analysisResult.qc })
        : "No VCF has been analyzed yet.";
        
      // Format history
      const history = messages.filter(m => !m.isClinicalReport).map(m => ({
        role: m.role,
        content: m.content
      }));

      const response = await chat({
        message: userMsg,
        context: context,
        history: history
      });

      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: response.response
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: `Sorry, I couldn't process that: ${err.message}`
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="card fade-in" style={{ display: 'flex', height: 'calc(100vh - 80px)', gap: 24, padding: 0, overflow: 'hidden' }}>
      
      {/* ── Left Panel: Analysis Pipeline ──────────────────────────── */}
      <div style={{ width: '350px', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 20, borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: 16 }}>Clinical Pipeline</h2>
          
          <div 
            style={{
              border: `2px dashed ${file ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 8, padding: 24, textAlign: 'center',
              backgroundColor: file ? 'rgba(59,130,246,0.05)' : 'transparent',
              transition: 'all 0.2s', cursor: 'pointer'
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => document.getElementById('vcf-upload').click()}
          >
            <input type="file" id="vcf-upload" hidden accept=".vcf,.vcf.gz" onChange={handleFileSelect} />
            <UploadCloud size={32} color="var(--accent)" style={{ marginBottom: 12 }} />
            {file ? (
              <div>
                <div style={{ fontWeight: 500 }}>{file.name}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {(file.size / 1024).toFixed(1)} KB
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-secondary)' }}>
                Drag & Drop patient .VCF here<br/>or click to browse
              </div>
            )}
          </div>
          
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={analyzing}
              style={{
                padding: '8px 12px',
                borderRadius: 8,
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                cursor: analyzing ? 'not-allowed' : 'pointer'
              }}
            >
              <option value="xgboost">XGBoost (Recommended)</option>
              <option value="random_forest">Random Forest</option>
              <option value="lightgbm">LightGBM</option>
              <option value="mlp_neural_network">Neural Network (MLP)</option>
              <option value="logistic_regression">Logistic Regression</option>
            </select>
            <div style={{ display: 'flex', gap: 8 }}>
              <button 
                className="btn btn-primary" 
                style={{ flex: 1 }}
                disabled={!file || analyzing}
                onClick={startAnalysis}
              >
                {analyzing ? <Loader2 size={16} className="spin" /> : 'Run Analysis'}
              </button>
              <a 
                href={getSampleVcfUrl()} 
                download 
                className="btn btn-secondary"
                title="Download Demo VCF"
                style={{ padding: '8px 12px' }}
              >
                <Download size={16} />
              </a>
            </div>
          </div>
        </div>

        {/* Pipeline Stepper */}
        <div style={{ padding: 20, flex: 1, overflowY: 'auto' }}>
          <h3 style={{ fontSize: '0.9rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: 16 }}>
            Status
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Step 
              label="VCF Parsing & Annotation" 
              active={analyzing} 
              done={!!analysisResult} 
            />
            <Step 
              label="Quality Control (QC)" 
              active={analyzing && !analysisResult} 
              done={!!analysisResult} 
            />
            <Step 
              label="Pathogenicity Prediction" 
              active={analyzing && !analysisResult} 
              done={!!analysisResult} 
            />
            <Step 
              label="Knowledge Retrieval (RAG)" 
              active={analyzing && !analysisResult} 
              done={!!analysisResult} 
            />
            <Step 
              label="Clinical Summary Generation" 
              active={analyzing && !analysisResult} 
              done={!!analysisResult} 
            />
          </div>
        </div>
      </div>

      {/* ── Right Panel: Chat Interface ───────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: 'var(--surface-50)' }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, backgroundColor: 'var(--surface)' }}>
          <Bot size={24} color="var(--accent)" />
          <div>
            <div style={{ fontWeight: 600 }}>GeneTrustAI Assistant</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--success)' }}>● Online</div>
          </div>
        </div>

        <div style={{ flex: 1, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
          {messages.map(msg => (
            <div key={msg.id} style={{
              display: 'flex', gap: 16,
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                backgroundColor: msg.role === 'user' ? 'var(--surface-200)' : 'rgba(59,130,246,0.1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
              }}>
                {msg.role === 'user' ? <User size={18} /> : <Bot size={18} color="var(--accent)" />}
              </div>
              
              <div style={{
                maxWidth: '75%',
                backgroundColor: msg.role === 'user' ? 'var(--text-primary)' : 'var(--surface)',
                color: msg.role === 'user' ? 'white' : 'inherit',
                padding: '12px 16px',
                borderRadius: 12,
                borderTopRightRadius: msg.role === 'user' ? 4 : 12,
                borderTopLeftRadius: msg.role === 'assistant' ? 4 : 12,
                border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
                boxShadow: msg.role === 'user' ? 'none' : '0 2px 4px rgba(0,0,0,0.02)'
              }}>
                {msg.isClinicalReport && msg.qc && (
                  <div style={{ marginBottom: 16, padding: 12, backgroundColor: 'var(--surface-50)', borderRadius: 8, border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>QC Score: {msg.qc.score}%</span>
                      <span style={{ 
                        fontSize: '0.8rem', fontWeight: 600, padding: '2px 8px', borderRadius: 12,
                        backgroundColor: msg.qc.status === 'PASS' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                        color: msg.qc.status === 'PASS' ? 'var(--success)' : 'var(--danger)'
                      }}>
                        {msg.qc.status}
                      </span>
                    </div>
                    {msg.variants?.length > 0 && (
                      <div style={{ fontSize: '0.85rem' }}>
                        Detected <strong>{msg.variants.length}</strong> HBB variants. Top finding: <br/>
                        <code style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>
                          chr{msg.variants[0].chr}:{msg.variants[0].pos} {msg.variants[0].ref}&gt;{msg.variants[0].alt}
                        </code>
                        <span style={{ marginLeft: 8, padding: '2px 6px', borderRadius: 4, backgroundColor: 'var(--surface-200)' }}>
                          {msg.variants[0].pathogenicity}
                        </span>
                      </div>
                    )}
                  </div>
                )}
                
                <div className="prose" style={{ fontSize: '0.95rem', lineHeight: 1.6 }}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          {sending && (
            <div style={{ display: 'flex', gap: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', backgroundColor: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Loader2 size={18} color="var(--accent)" className="spin" />
              </div>
              <div style={{ padding: '12px 16px', backgroundColor: 'var(--surface)', borderRadius: 12, borderTopLeftRadius: 4, border: '1px solid var(--border)' }}>
                <span className="typing-dots">Thinking</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ padding: 20, borderTop: '1px solid var(--border)', backgroundColor: 'var(--surface)' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
            <textarea 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={analysisResult ? "Ask follow-up questions about this VCF..." : "Upload a VCF to begin..."}
              disabled={!analysisResult || sending}
              style={{
                flex: 1, resize: 'none', padding: '12px 16px',
                borderRadius: 8, border: '1px solid var(--border)',
                minHeight: '44px', maxHeight: '120px', fontFamily: 'inherit'
              }}
              rows={1}
            />
            <button 
              className="btn btn-primary"
              onClick={handleSend}
              disabled={!input.trim() || !analysisResult || sending}
              style={{ height: 44, width: 44, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
      
    </div>
  );
}

function Step({ label, active, done }) {
  let icon = <Clock size={18} color="var(--text-secondary)" />;
  let color = 'var(--text-secondary)';
  
  if (done) {
    icon = <CheckCircle size={18} color="var(--success)" />;
    color = 'var(--text-primary)';
  } else if (active) {
    icon = <Loader2 size={18} color="var(--accent)" className="spin" />;
    color = 'var(--accent)';
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: (!active && !done) ? 0.5 : 1 }}>
      {icon}
      <span style={{ fontSize: '0.9rem', color, fontWeight: active ? 600 : 400 }}>{label}</span>
    </div>
  );
}
