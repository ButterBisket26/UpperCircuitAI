import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { MessageBubble } from '../components/MessageBubble';
import { Columns, Play, Sparkles, Building2, HelpCircle } from 'lucide-react';

export const Compare = () => {
  const [companies, setCompanies] = useState([]);
  
  // Left Column States
  const [ticker1, setTicker1] = useState('');
  const [period1, setPeriod1] = useState('');
  const [filings1, setFilings1] = useState([]);
  
  // Right Column States
  const [ticker2, setTicker2] = useState('');
  const [period2, setPeriod2] = useState('');
  const [filings2, setFilings2] = useState([]);
  
  // Query States
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Comparison Results
  const [result1, setResult1] = useState(null);
  const [result2, setResult2] = useState(null);

  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      const data = await api.listCompanies();
      const activeCompanies = data.filter(c => c.filing_count > 0);
      setCompanies(activeCompanies);
      
      // Auto fill default values if available
      if (activeCompanies.length > 0) {
        setTicker1(activeCompanies[0].ticker);
        if (activeCompanies.length > 1) {
          setTicker2(activeCompanies[1].ticker);
        } else {
          setTicker2(activeCompanies[0].ticker);
        }
      }
    } catch (err) {
      console.error("Compare: Failed to load companies directory.", err);
    }
  };

  // Fetch filings when selected ticker changes for Col 1
  useEffect(() => {
    if (ticker1) {
      api.listFilings(ticker1).then(data => {
        setFilings1(data.filter(f => f.status === 'processed'));
        if (data.length > 0) {
          setPeriod1(data[0].fiscal_period);
        }
      });
    }
  }, [ticker1]);

  // Fetch filings when selected ticker changes for Col 2
  useEffect(() => {
    if (ticker2) {
      api.listFilings(ticker2).then(data => {
        setFilings2(data.filter(f => f.status === 'processed'));
        if (data.length > 0) {
          setPeriod2(data[0].fiscal_period);
        }
      });
    }
  }, [ticker2]);

  const handleRunComparison = async (e) => {
    e.preventDefault();
    if (!question.trim()) {
      setErrorMsg("Please enter an analytical question to compare.");
      return;
    }
    if (!ticker1 || !ticker2 || !period1 || !period2) {
      setErrorMsg("Please select ticker and period filters for both columns.");
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setResult1(null);
    setResult2(null);

    try {
      // Query both pipelines in parallel
      const [res1, res2] = await Promise.all([
        api.query(question, ticker1, null, period1),
        api.query(question, ticker2, null, period2)
      ]);

      setResult1({
        ticker: ticker1,
        period: period1,
        answer: res1.answer,
        latency: res1.latency_ms,
        chunks: res1.chunks_used,
        citations: res1.citations
      });

      setResult2({
        ticker: ticker2,
        period: period2,
        answer: res2.answer,
        latency: res2.latency_ms,
        chunks: res2.chunks_used,
        citations: res2.citations
      });

    } catch (err) {
      setErrorMsg("Failed to complete double pipeline comparison queries. Verify backend is running.");
    } finally {
      setLoading(false);
    }
  };

  // Highlights financial quantities, percentages, and metrics to emphasize changes
  const renderHighlightedText = (text) => {
    if (!text) return '';
    // Regex for financial values (e.g. Rs 2,341, 12.5%, 38,821 crore, 20.5 percent)
    const financialRegex = /(\b(?:Rs\.?\s*)?\d+(?:,\d+)*(?:\.\d+)?\s*(?:crore|lakh|percent|%)\b|\b\d+(?:,\d+)*(?:\.\d+)?%|\bRs\s*\d+(?:,\d+)*(?:\.\d+)?\b)/gi;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = financialRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      parts.push(
        <mark 
          key={match.index} 
          className="theme-highlight border px-1 py-0.5 rounded font-bold font-mono text-xs select-all inline-block"
        >
          {match[0]}
        </mark>
      );
      lastIndex = financialRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-73px)] theme-bg font-sans overflow-hidden">
      
      {/* Control Input Header Form */}
      <div className="border-b theme-border theme-bg p-5">
        <form onSubmit={handleRunComparison} className="max-w-6xl mx-auto w-full space-y-4">
          
          <div className="flex flex-col md:flex-row items-center gap-4">
            
            {/* Left Selection */}
            <div className="flex-1 grid grid-cols-2 gap-2 w-full">
              <select
                value={ticker1}
                onChange={(e) => setTicker1(e.target.value)}
                className="theme-input rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
              >
                <option value="">Select Company A</option>
                {companies.map(c => (
                  <option key={c.id} value={c.ticker}>{c.ticker} - {c.name}</option>
                ))}
              </select>

              <select
                value={period1}
                onChange={(e) => setPeriod1(e.target.value)}
                className="theme-input rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                disabled={filings1.length === 0}
              >
                {filings1.length === 0 ? (
                  <option>No filings indexed</option>
                ) : (
                  filings1.map(f => (
                    <option key={f.id} value={f.fiscal_period}>{f.fiscal_period} ({f.report_type})</option>
                  ))
                )}
              </select>
            </div>

            {/* Vs Separator badge */}
            <div className="text-slate-500 text-xs font-bold font-mono tracking-wider uppercase select-none">
              VS
            </div>

            {/* Right Selection */}
            <div className="flex-1 grid grid-cols-2 gap-2 w-full">
              <select
                value={ticker2}
                onChange={(e) => setTicker2(e.target.value)}
                className="theme-input rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
              >
                <option value="">Select Company B</option>
                {companies.map(c => (
                  <option key={c.id} value={c.ticker}>{c.ticker} - {c.name}</option>
                ))}
              </select>

              <select
                value={period2}
                onChange={(e) => setPeriod2(e.target.value)}
                className="theme-input rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-500"
                disabled={filings2.length === 0}
              >
                {filings2.length === 0 ? (
                  <option>No filings indexed</option>
                ) : (
                  filings2.map(f => (
                    <option key={f.id} value={f.fiscal_period}>{f.fiscal_period} ({f.report_type})</option>
                  ))
                )}
              </select>
            </div>
            
          </div>

          {/* Question Input bar */}
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Ask an analytical question comparing figures (e.g. 'Compare revenues, net profits, and operating margins')"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="flex-1 theme-input text-xs placeholder-slate-500 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-500 transition-colors"
            />
            
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-3 rounded-xl font-semibold text-xs bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-500/10 flex items-center gap-2 transition-all duration-300 disabled:opacity-50"
            >
              <Play size={14} className={loading ? 'animate-spin' : ''} />
              <span>{loading ? 'Analyzing...' : 'Compare'}</span>
            </button>
          </div>

        </form>
      </div>

      {/* COMPARISON DISPLAY columns */}
      <div className="flex-1 overflow-y-auto p-6 theme-bg">
        <div className="max-w-6xl mx-auto w-full h-full">
          {errorMsg && (
            <div className="p-3 bg-red-950/20 border border-red-900/30 text-red-400 rounded-xl text-xs mb-4">
              {errorMsg}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-[50vh] text-center">
              <Columns className="text-blue-500 animate-pulse mb-3" size={36} />
              <h4 className="text-slate-300 font-semibold text-sm">Synthesizing Comparative Analysis...</h4>
              <p className="text-xs text-slate-500 mt-1">UpperCircuitAI is running double hybrid retrieval tasks concurrently.</p>
            </div>
          ) : result1 && result2 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full items-start">
              
              {/* LEFT Column answer details */}
              <div className="rounded-2xl theme-panel border p-5 space-y-4">
                <div className="flex items-center justify-between border-b theme-border pb-3">
                  <div>
                    <span className="text-xs font-bold text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-lg">{result1.ticker}</span>
                    <span className="text-xs theme-text-secondary font-mono font-bold ml-2">{result1.period} Report</span>
                  </div>
                  <div className="text-[10px] font-mono theme-text-muted">
                    Latency: {result1.latency}ms • {result1.chunks} chunks
                  </div>
                </div>
                
                <div className="theme-text-primary text-xs leading-relaxed font-sans whitespace-pre-line theme-card p-4 rounded-xl border">
                  {renderHighlightedText(result1.answer)}
                </div>
              </div>

              {/* RIGHT Column answer details */}
              <div className="rounded-2xl theme-panel border p-5 space-y-4">
                <div className="flex items-center justify-between border-b theme-border pb-3">
                  <div>
                    <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-lg">{result2.ticker}</span>
                    <span className="text-xs theme-text-secondary font-mono font-bold ml-2">{result2.period} Report</span>
                  </div>
                  <div className="text-[10px] font-mono theme-text-muted">
                    Latency: {result2.latency}ms • {result2.chunks} chunks
                  </div>
                </div>
                
                <div className="theme-text-primary text-xs leading-relaxed font-sans whitespace-pre-line theme-card p-4 rounded-xl border">
                  {renderHighlightedText(result2.answer)}
                </div>
              </div>

            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[50vh] text-center border-2 border-dashed theme-border rounded-2xl p-6">
              <Sparkles className="text-slate-650 mb-3" size={32} />
              <h4 className="theme-text-secondary font-semibold text-xs">Run Side-by-Side Comparison</h4>
              <p className="text-xs theme-text-muted max-w-sm mt-1 leading-relaxed">
                Select companies and fiscal periods in both columns, then submit an analytical question to compare numeric trends.
              </p>
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default Compare;
