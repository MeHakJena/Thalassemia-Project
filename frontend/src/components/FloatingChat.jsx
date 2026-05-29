import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, User, Loader2 } from 'lucide-react';
import { chat } from '../api';
import ReactMarkdown from 'react-markdown';
import { useAppContext } from '../context/AppContext';

export default function FloatingChat() {
  const { pageContext } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I am BETA-AI. How can I assist you with this application today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    
    const userMsg = input.trim();
    setInput('');
    setSending(true);
    
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: userMsg }]);

    try {
      const history = messages.map(m => ({
        role: m.role,
        content: m.content
      }));

      // Passing dynamic context based on the user's active page
      const response = await chat({
        message: userMsg,
        context: `Context regarding what the user is currently viewing on their screen: ${pageContext}\n\nPlease use this context to answer their question appropriately.`,
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
        content: `Error: ${err.message}`
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
    <>
      {/* Floating Action Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`floating-chat-btn ${isOpen ? 'open' : ''}`}
        aria-label="Toggle AI Assistant"
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="floating-chat-window fade-in-up">
          <div className="floating-chat-header">
            <Bot size={20} color="var(--accent)" />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <strong>BETA-AI Assistant</strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● Online</span>
            </div>
            <button className="close-btn" onClick={() => setIsOpen(false)}>
              <X size={18} />
            </button>
          </div>

          <div className="floating-chat-messages">
            {messages.map(msg => (
              <div key={msg.id} className={`chat-message-row ${msg.role === 'user' ? 'user-row' : 'assistant-row'}`}>
                <div className="chat-avatar">
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={14} color="var(--accent)" />}
                </div>
                <div className={`chat-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`}>
                  <div className="prose" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {sending && (
              <div className="chat-message-row assistant-row">
                <div className="chat-avatar"><Loader2 size={14} color="var(--accent)" className="spin" /></div>
                <div className="chat-bubble assistant-bubble">
                  <span className="typing-dots">Thinking</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="floating-chat-input">
            <textarea 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              disabled={sending}
              rows={1}
            />
            <button onClick={handleSend} disabled={!input.trim() || sending}>
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
