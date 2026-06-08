import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';

export const CitationCard = ({ citation }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { company, report_type, fiscal_period, page_number, chunk_preview } = citation;

  return (
    <div className="rounded-xl border theme-card theme-card-hover overflow-hidden transition-all duration-200 shadow-sm">
      {/* Accordion header trigger */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3.5 text-left select-none"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <FileText size={16} />
          </div>
          <div>
            <div className="font-bold text-xs theme-text-primary tracking-wide uppercase">
              {company}
            </div>
            <div className="text-[11px] theme-text-secondary mt-0.5">
              {report_type.charAt(0).toUpperCase() + report_type.slice(1)} • {fiscal_period} • Page {page_number}
            </div>
          </div>
        </div>
        
        <div className="theme-text-secondary hover:theme-text-primary p-1 rounded-lg hover:bg-slate-800/40 transition-colors">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {/* Accordion content body */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t theme-border bg-black/10">
          <div className="text-[10px] font-mono theme-text-muted pt-3 uppercase tracking-wider font-semibold">
            Context Chunk Preview
          </div>
          <div className="text-xs theme-text-secondary leading-relaxed font-sans mt-2 whitespace-pre-line border-l-2 border-indigo-500/30 pl-3">
            "{chunk_preview}"
          </div>
        </div>
      )}
    </div>
  );
};

export default CitationCard;
