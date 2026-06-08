import React from 'react';
import { CitationCard } from './CitationCard';

export const MessageBubble = ({ message }) => {
  const { sender, text, citations, chunks_used, latency_ms } = message;
  const isUser = sender === 'user';

  // Replaces inline bracketed citations [Company | Type | Period | Page N] with clean badges
  const renderMessageContent = (content) => {
    const citationRegex = /\[([^\|\]]+)\s*\|\s*([^\|\]]+)\s*\|\s*([^\|\]]+)\s*\|\s*(?:Page\s*)?(\d+)\]/gi;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }

      const [fullMatch, company, type, period, page] = match;
      const cleanCompany = company.trim().substring(0, 6).toUpperCase();
      const cleanPeriod = period.trim().upper ? period.trim().toUpperCase() : period.trim();
      const cleanPage = page.trim();

      parts.push(
        <span 
          key={match.index}
          className="inline-flex items-center align-super mx-0.5 px-1.5 py-0.5 text-[9px] font-bold font-mono tracking-tight bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded select-none cursor-help"
          title={`Source: ${company} | ${type} | ${period} | Page ${page}`}
        >
          {cleanCompany}•{cleanPeriod}•P{cleanPage}
        </span>
      );

      lastIndex = citationRegex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return parts.length > 0 ? parts : content;
  };

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        
        {/* Main message bubble */}
        <div className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-sm font-sans whitespace-pre-line ${
          isUser 
            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-none'
            : 'theme-card border theme-text-primary rounded-bl-none'
        }`}>
          {isUser ? text : renderMessageContent(text)}
        </div>

        {/* Small latency/retrieval metadata info for AI messages */}
        {!isUser && (chunks_used !== undefined || latency_ms !== undefined) && (
          <div className="flex items-center gap-3 mt-1.5 px-1 text-[10px] theme-text-muted font-medium font-mono select-none">
            {latency_ms !== undefined && (
              <span>Latency: <strong className="theme-text-secondary">{latency_ms}ms</strong></span>
            )}
            {chunks_used !== undefined && (
              <span>• Context: <strong className="theme-text-secondary">{chunks_used} chunks</strong></span>
            )}
          </div>
        )}

        {/* Collapsible Citation list for AI messages */}
        {!isUser && citations && citations.length > 0 && (
          <div className="w-full mt-3 flex flex-col gap-2">
            <div className="text-[10px] theme-text-muted font-semibold uppercase tracking-wider pl-1">
              Source Citations ({citations.length})
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full">
              {citations.map((cite, index) => (
                <CitationCard key={index} citation={cite} />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default MessageBubble;
