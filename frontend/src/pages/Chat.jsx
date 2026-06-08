import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { MessageBubble } from '../components/MessageBubble';
import { Send, Sparkles, Filter, RefreshCw } from 'lucide-react';

export const Chat = () => {
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: "Hello! I am UpperCircuitAI, your specialized Indian financial filing RAG assistant.\n\nSelect a company scope filter above or ask me any question about the indexed annual reports. I will answer grounded on official text and extract exact page citations."
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [selectedTicker, setSelectedTicker] = useState('');
  const [companiesList, setCompaniesList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const messagesEndRef = useRef(null);

  // Suggested questions
  const SUGGESTIONS = [
    { text: "What was ITC segment revenue in FY25?", ticker: "ITC" },
    { text: "What was TCS operating margin in FY24?", ticker: "TCS" },
    { text: "Reliance Industries consolidated EBITDA for FY24?", ticker: "RELIANCE" },
    { text: "Infosys revenue & profit in FY24?", ticker: "INFY" }
  ];

  const checkStatus = async () => {
    try {
      const data = await api.checkIngestStatus();
      setIsIngesting(data.ingesting);
    } catch (err) {
      console.error("Chat: Failed to check ingestion status.", err);
    }
  };

  useEffect(() => {
    fetchCompanies();
    checkStatus();
    const interval = setInterval(checkStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!isIngesting) {
      fetchCompanies();
    }
  }, [isIngesting]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const fetchCompanies = async () => {
    try {
      const data = await api.listCompanies();
      // Filter out companies with 0 filings
      setCompaniesList(data.filter(c => c.filing_count > 0));
    } catch (err) {
      console.error("Chat: Failed to load company list.", err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (textToSend) => {
    const queryText = textToSend || inputValue.trim();
    if (!queryText) return;

    if (!textToSend) {
      setInputValue('');
    }

    // Append user message
    const userMsg = { sender: 'user', text: queryText };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      // Query RAG pipeline
      const data = await api.query(queryText, selectedTicker || null);
      
      const aiResponse = {
        sender: 'ai',
        text: data.answer,
        citations: data.citations,
        chunks_used: data.chunks_used,
        latency_ms: data.latency_ms
      };
      
      setMessages(prev => [...prev, aiResponse]);
    } catch (err) {
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: "Error: Could not retrieve answer. Make sure the backend server is running and models are fully initialized."
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (sug) => {
    setSelectedTicker(sug.ticker);
    handleSendMessage(sug.text);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-73px)] theme-bg font-sans">
      
      {/* Scope Filter Banner */}
      <div className="border-b theme-border theme-bg px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 theme-text-secondary text-xs">
          <Filter size={14} className="text-blue-400" />
          <span>Filing Scope Filter:</span>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            className="ml-2 theme-input rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-blue-500"
          >
            <option value="">All Indexed Companies</option>
            {companiesList.map(c => (
              <option key={c.id} value={c.ticker}>{c.name} ({c.ticker})</option>
            ))}
          </select>
        </div>
        
        {isIngesting ? (
          <div className="flex items-center gap-1.5 text-[10px] text-amber-500 font-mono animate-pulse">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Ingestion processing</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[10px] theme-text-muted font-mono">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span>RAG Pipeline Online</span>
          </div>
        )}
      </div>

      {/* Chat Messages Panel */}
      <div className="flex-1 overflow-y-auto px-6 py-6 scroll-smooth">
        <div className="max-w-4xl mx-auto w-full">
          {messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} />
          ))}
          
          {loading && (
            <div className="flex w-full justify-start mb-6">
              <div className="theme-card border px-5 py-3.5 rounded-2xl rounded-bl-none max-w-[80%] flex items-center gap-3">
                <RefreshCw className="animate-spin text-blue-400" size={16} />
                <span className="text-xs theme-text-secondary font-medium font-sans">UpperCircuitAI is analyzing filings and synthesizing answer...</span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* suggestion buttons and bottom input bar */}
      <div className="border-t theme-border theme-nav px-6 py-4">
        <div className="max-w-4xl mx-auto w-full">
          
          {/* Suggestions List */}
          {messages.length === 1 && (
            <div className="mb-4">
              <div className="text-[10px] font-semibold theme-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Sparkles size={12} className="text-blue-400" />
                <span>Suggested Questions</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((sug, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(sug)}
                    className="px-3.5 py-1.5 text-xs text-left theme-card theme-card-hover theme-text-secondary border rounded-xl transition-all duration-300"
                  >
                    {sug.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Form input bar */}
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Ask a financial filing question (e.g. 'What was TCS net profit in FY24?')"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={loading}
              className="flex-1 theme-input text-sm placeholder-slate-505 rounded-2xl px-5 py-3.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 disabled:opacity-50 transition-all duration-300"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !inputValue.trim()}
              className="p-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-2xl shadow-lg shadow-indigo-600/10 hover:shadow-indigo-600/25 flex items-center justify-center transition-all duration-300 disabled:opacity-40 disabled:hover:scale-100 hover:scale-105"
            >
              <Send size={18} />
            </button>
          </div>
          
        </div>
      </div>

    </div>
  );
};

export default Chat;
