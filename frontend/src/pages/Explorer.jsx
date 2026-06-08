import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { CompanySearch } from '../components/CompanySearch';
import { FilingUpload } from '../components/FilingUpload';
import { FileText, Building2, ChevronRight, Activity, Calendar, Server, Trash2 } from 'lucide-react';

export const Explorer = () => {
  const [companies, setCompanies] = useState([]);
  const [filteredCompanies, setFilteredCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedCompanyFilings, setSelectedCompanyFilings] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [loadingFilings, setLoadingFilings] = useState(false);

  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const data = await api.listCompanies();
      setCompanies(data);
      setFilteredCompanies(data);
      
      // Auto-select first company if available and none selected
      if (data.length > 0 && !selectedCompany) {
        handleSelectCompany(data[0]);
      }
    } catch (err) {
      console.error("Explorer: Failed to load companies.", err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const handleSelectCompany = async (company) => {
    setSelectedCompany(company);
    setLoadingFilings(true);
    try {
      const filings = await api.listFilings(company.ticker);
      setSelectedCompanyFilings(filings);
    } catch (err) {
      console.error(`Explorer: Failed to load filings for ${company.ticker}`, err);
      setSelectedCompanyFilings([]);
    } finally {
      setLoadingFilings(false);
    }
  };

  const handleDeleteFiling = async (filing) => {
    if (!window.confirm(`Are you sure you want to delete the filing ${filing.report_type.toUpperCase()} - ${filing.fiscal_period} for ${selectedCompany.ticker}?`)) {
      return;
    }
    try {
      await api.deleteFiling(filing.id);
      // Refresh filings
      const filings = await api.listFilings(selectedCompany.ticker);
      setSelectedCompanyFilings(filings);
      // Refresh companies directory (updates count)
      fetchCompanies();
    } catch (err) {
      alert("Failed to delete filing: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleSearch = (term) => {
    const lower = term.toLowerCase();
    const filtered = companies.filter(
      c => c.name.toLowerCase().includes(lower) || c.ticker.toLowerCase().includes(lower)
    );
    setFilteredCompanies(filtered);
  };

  const getStatusBadge = (status) => {
    const maps = {
      processed: 'bg-green-500/10 text-green-400 border border-green-500/20',
      pending: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse',
      failed: 'bg-red-500/10 text-red-400 border border-red-500/20'
    };
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase ${maps[status] || maps.pending}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 h-[calc(100vh-73px)] theme-bg font-sans overflow-hidden">
      
      {/* LEFT PANEL: Company Directory Search */}
      <div className="lg:col-span-5 border-r theme-border flex flex-col h-full">
        
        <div className="p-5 border-b theme-border theme-bg">
          <h2 className="text-base font-bold theme-text-primary font-display mb-3">Company Directory</h2>
          <CompanySearch onSearch={handleSearch} />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loadingCompanies ? (
            <div className="text-center py-10 text-xs text-slate-500">Loading directory...</div>
          ) : filteredCompanies.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-500">No indexed companies matching query.</div>
          ) : (
            filteredCompanies.map((company) => (
              <div
                key={company.id}
                onClick={() => handleSelectCompany(company)}
                className={`flex items-center justify-between p-3.5 rounded-xl cursor-pointer select-none transition-all duration-300 ${
                  selectedCompany?.ticker === company.ticker
                    ? 'bg-blue-500/10 border border-blue-500/30'
                    : 'theme-card theme-card-hover border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                    selectedCompany?.ticker === company.ticker
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'theme-card text-slate-400'
                  }`}>
                    <Building2 size={16} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs theme-text-primary">{company.ticker}</span>
                      <span className="text-[10px] font-semibold theme-card px-1.5 py-0.5 rounded theme-text-muted border">{company.exchange}</span>
                    </div>
                    <div className="text-[11px] theme-text-secondary mt-0.5 truncate max-w-[180px]">{company.name}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono theme-text-muted theme-bg border px-2 py-0.5 rounded-lg">
                    {company.filing_count} filings
                  </span>
                  <ChevronRight size={14} className="text-slate-600" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* RIGHT PANEL: Selected Filings Browser + Ingester */}
      <div className="lg:col-span-7 flex flex-col h-full overflow-y-auto p-6 theme-bg">
        
        {selectedCompany ? (
          <div className="space-y-6">
            
            {/* Header info */}
            <div className="p-5 rounded-2xl theme-panel border flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-lg font-bold font-display theme-text-primary">{selectedCompany.name}</h1>
                  <span className="text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded">{selectedCompany.ticker}</span>
                </div>
                <div className="text-xs theme-text-secondary">
                  ISIN: <span className="font-mono text-slate-350">{selectedCompany.isin}</span> • Sector: <span className="text-slate-350">{selectedCompany.sector || 'N/A'}</span>
                </div>
              </div>
              
              <div className="text-right">
                <span className="text-[10px] theme-text-muted font-bold block uppercase tracking-wider mb-0.5">Exchange listed</span>
                <span className="text-sm font-bold text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-xl border border-indigo-500/20">{selectedCompany.exchange} Market</span>
              </div>
            </div>

            {/* List of filings */}
            <div>
              <h3 className="text-xs font-semibold theme-text-muted uppercase tracking-wider mb-3 pl-1">Indexed filings</h3>
              
              {loadingFilings ? (
                <div className="text-center py-10 text-xs theme-text-muted">Loading filing reports...</div>
              ) : selectedCompanyFilings.length === 0 ? (
                <div className="text-center py-10 text-xs theme-text-muted border theme-border rounded-2xl">
                  No filings indexed for this company. Trigger ingestion below to parse documents.
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedCompanyFilings.map((filing) => (
                    <div 
                      key={filing.id}
                      className="p-4 rounded-xl border theme-card theme-card-hover flex items-center justify-between gap-4 transition-all duration-300"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
                          <FileText size={16} />
                        </div>
                        <div>
                          <div className="font-semibold text-xs theme-text-primary uppercase">
                            {filing.report_type} • {filing.fiscal_period}
                          </div>
                          <div className="text-[10px] theme-text-muted mt-1 flex items-center gap-2">
                            <span className="flex items-center gap-1"><Calendar size={10} /> Filing Date: {filing.filing_date || 'N/A'}</span>
                            <span className="flex items-center gap-1"><Server size={10} /> Chunks: {filing.chunk_count}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {getStatusBadge(filing.status)}
                        {filing.pdf_url && filing.pdf_url.startsWith('http') && (
                          <a
                            href={filing.pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
                            title="Open Original Announcement PDF"
                          >
                            📎
                          </a>
                        )}
                        <button
                          onClick={() => handleDeleteFiling(filing)}
                          className="p-1.5 rounded-lg bg-red-950/20 hover:bg-red-900/40 text-red-400 hover:text-red-300 border border-red-900/35 transition-colors flex items-center justify-center"
                          title="Delete Filing"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Ingestion section */}
            <div>
              <h3 className="text-xs font-semibold theme-text-muted uppercase tracking-wider mb-3 pl-1">Ingest new filing</h3>
              <FilingUpload onIngestComplete={fetchCompanies} />
            </div>

          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col items-center justify-center text-center theme-text-muted p-4 border border-dashed theme-border rounded-2xl theme-card">
              <Building2 size={32} className="text-slate-600 mb-2" />
              <h4 className="font-semibold theme-text-secondary text-xs mb-1">No Company Selected</h4>
              <p className="text-[11px] theme-text-muted max-w-xs leading-relaxed">
                Select an indexed company from the directory, or index a new company filing report below.
              </p>
            </div>
            
            <div>
              <h3 className="text-xs font-semibold theme-text-muted uppercase tracking-wider mb-3 pl-1">Ingest new filing</h3>
              <FilingUpload onIngestComplete={fetchCompanies} />
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default Explorer;
