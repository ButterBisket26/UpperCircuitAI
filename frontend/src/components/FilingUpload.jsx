import React, { useState, useRef } from 'react';
import { api } from '../api/client';
import { Upload, File, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';

export const FilingUpload = ({ onIngestComplete }) => {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' or 'scrape'
  
  // Scrape/Metadata Form States
  const [ticker, setTicker] = useState('');
  const [exchange, setExchange] = useState('NSE');
  const [reportType, setReportType] = useState('annual');
  const [fiscalPeriod, setFiscalPeriod] = useState('');
  const [file, setFile] = useState(null);
  
  // Pipeline status states
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [ingestStatus, setIngestStatus] = useState('idle'); // 'idle' | 'running' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');
  const [resultMsg, setResultMsg] = useState('');
  
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
      } else {
        alert("Only PDF filing reports are supported.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const resetForm = () => {
    setTicker('');
    setFiscalPeriod('');
    setFile(null);
    setIngestStatus('idle');
    setProgress(0);
    setErrorMsg('');
  };

  const handleScrapeIngest = async (e) => {
    e.preventDefault();
    if (!ticker || !fiscalPeriod) {
      setErrorMsg("Please fill in Ticker symbol and Fiscal Period.");
      return;
    }
    
    setIngestStatus('running');
    setErrorMsg('');
    setProgress(35); // Scraper running state
    
    try {
      const response = await api.ingest(
        ticker.trim().toUpperCase(),
        exchange,
        reportType,
        fiscalPeriod.trim().toUpperCase()
      );
      
      setProgress(100);
      setIngestStatus('success');
      setResultMsg(`Scrape initiated for ${ticker.toUpperCase()}. status: ${response.status}. Background worker started.`);
      
      if (onIngestComplete) {
        onIngestComplete();
      }
    } catch (err) {
      setIngestStatus('error');
      setErrorMsg(err.response?.data?.detail || "Filing report was not found on Screener.in.");
    }
  };

  const handleUploadIngest = async (e) => {
    e.preventDefault();
    if (!ticker || !fiscalPeriod || !file) {
      setErrorMsg("Please fill in all form fields and attach a PDF filing.");
      return;
    }

    setIngestStatus('running');
    setErrorMsg('');
    setProgress(10);

    try {
      const response = await api.upload(
        ticker.trim().toUpperCase(),
        exchange,
        reportType,
        fiscalPeriod.trim().toUpperCase(),
        file,
        (percent) => {
          // Adjust upload progress bar
          setProgress(Math.min(95, Math.round(10 + percent * 0.85)));
        }
      );

      setProgress(100);
      setIngestStatus('success');
      setResultMsg(`Filing uploaded successfully. Background parser indexing initialized.`);
      
      if (onIngestComplete) {
        onIngestComplete();
      }
    } catch (err) {
      setIngestStatus('error');
      setErrorMsg(err.response?.data?.detail || "Filing ingestion job failed.");
    }
  };

  return (
    <div className="w-full theme-panel border rounded-2xl overflow-hidden shadow-lg shadow-black/40">
      
      {/* Toggle Tabs */}
      <div className="flex border-b theme-border bg-black/10">
        <button
          onClick={() => { setActiveTab('upload'); resetForm(); }}
          className={`flex-1 py-3 text-sm font-semibold border-b-2 transition-all duration-300 ${
            activeTab === 'upload'
              ? 'border-blue-500 text-blue-400 bg-black/5'
              : 'border-transparent theme-text-secondary hover:theme-text-primary'
          }`}
        >
          📂 Upload PDF Report
        </button>
        <button
          onClick={() => { setActiveTab('scrape'); resetForm(); setReportType('annual'); }}
          className={`flex-1 py-3 text-sm font-semibold border-b-2 transition-all duration-300 ${
            activeTab === 'scrape'
              ? 'border-blue-500 text-blue-400 bg-black/5'
              : 'border-transparent theme-text-secondary hover:theme-text-primary'
          }`}
        >
          🌐 Scrape Screener.in
        </button>
      </div>

      <div className="p-6">
        
        {ingestStatus === 'running' && (
          <div className="flex flex-col items-center justify-center py-8">
            <RefreshCw className="animate-spin text-blue-500 mb-4" size={36} />
            <h4 className="theme-text-primary font-semibold mb-2">Ingesting Financial Document...</h4>
            <p className="text-xs theme-text-secondary mb-6 text-center max-w-sm">
              The pipeline is downloading/saving raw files, executing table extractions, computing dense embeddings, and updating searches.
            </p>
            <div className="w-full max-w-xs theme-card rounded-full h-2.5 overflow-hidden border">
              <div 
                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2.5 rounded-full transition-all duration-500" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <span className="text-[10px] font-mono theme-text-muted mt-2 font-bold">{progress}% completed</span>
          </div>
        )}

        {ingestStatus === 'success' && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle2 className="text-green-500 mb-4" size={40} />
            <h4 className="theme-text-primary font-semibold mb-2">Ingestion Job Queued</h4>
            <p className="text-xs theme-text-secondary max-w-sm mb-6 leading-relaxed">
              {resultMsg} You can monitor processing status under the company browse filings tab.
            </p>
            <button
              onClick={resetForm}
              className="px-5 py-2 text-xs font-semibold rounded-xl theme-card theme-card-hover theme-text-secondary border transition-colors"
            >
              Upload Another Filing
            </button>
          </div>
        )}

        {ingestStatus === 'error' && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertCircle className="text-red-500 mb-4" size={40} />
            <h4 className="theme-text-primary font-semibold mb-2">Ingestion Failed</h4>
            <p className="text-xs text-red-400/80 max-w-sm mb-6 leading-relaxed bg-red-950/20 border border-red-900/30 p-3 rounded-xl">
              {errorMsg}
            </p>
            <button
              onClick={() => setIngestStatus('idle')}
              className="px-5 py-2 text-xs font-semibold rounded-xl theme-card theme-card-hover theme-text-secondary border transition-colors"
            >
              Back to Form
            </button>
          </div>
        )}

        {ingestStatus === 'idle' && (
          <form onSubmit={activeTab === 'upload' ? handleUploadIngest : handleScrapeIngest} className="space-y-5">
            {errorMsg && (
              <div className="flex items-center gap-2 p-3 bg-red-950/20 border border-red-900/30 text-red-400 rounded-xl text-xs">
                <AlertCircle size={16} />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Drag & Drop File Input (Only in Upload Mode) */}
            {activeTab === 'upload' && (
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-300 ${
                  dragActive 
                    ? 'border-blue-500 bg-blue-500/5' 
                    : 'theme-border bg-black/5 hover:border-slate-400'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept=".pdf"
                />
                
                {file ? (
                  <div className="flex flex-col items-center justify-center">
                    <File className="text-blue-400 mb-2" size={32} />
                    <span className="text-xs theme-text-primary font-semibold truncate max-w-xs">{file.name}</span>
                    <span className="text-[10px] theme-text-muted mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB • Click to replace</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center">
                    <Upload className="theme-text-muted mb-2" size={32} />
                    <span className="text-xs theme-text-secondary font-semibold">Drag & drop company report PDF here</span>
                    <span className="text-[10px] theme-text-muted mt-1">or click to browse local folders</span>
                  </div>
                )}
              </div>
            )}

            {/* Input grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-[10px] font-semibold theme-text-muted uppercase tracking-wide mb-1.5 pl-1">
                  Ticker Symbol
                </label>
                <input
                  type="text"
                  placeholder="e.g. INFY, TCS, RELIANCE"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  className="w-full px-4 py-2.5 text-xs rounded-xl theme-input placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold theme-text-muted uppercase tracking-wide mb-1.5 pl-1">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  disabled={activeTab === 'scrape'}
                  className={`w-full px-4 py-2.5 text-xs rounded-xl theme-input focus:outline-none focus:border-blue-500 transition-colors ${
                    activeTab === 'scrape' ? 'cursor-not-allowed opacity-60' : ''
                  }`}
                >
                  <option value="annual">Annual Report</option>
                  <option value="quarterly">Quarterly Report</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-semibold theme-text-muted uppercase tracking-wide mb-1.5 pl-1">
                  Fiscal Period
                </label>
                <input
                  type="text"
                  placeholder={reportType === 'quarterly' ? "e.g. Q3FY25, Q4FY26" : "e.g. FY24, FY25"}
                  value={fiscalPeriod}
                  onChange={(e) => setFiscalPeriod(e.target.value)}
                  className="w-full px-4 py-2.5 text-xs rounded-xl theme-input focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full mt-2 py-3 rounded-xl font-semibold text-xs tracking-wide bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-600/10 transition-all duration-300"
            >
              {activeTab === 'upload' ? '📥 Index Uploaded Report' : '⚡ Trigger Scraping Job'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default FilingUpload;
