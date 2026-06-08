import React, { useState } from 'react';
import { Search } from 'lucide-react';

export const CompanySearch = ({ onSearch }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const handleInputChange = (e) => {
    const val = e.target.value;
    setSearchTerm(val);
    if (onSearch) {
      onSearch(val);
    }
  };

  return (
    <div className="relative w-full">
      {/* Search Icon */}
      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
        <Search size={16} />
      </div>
      
      {/* Search Input field */}
      <input
        type="text"
        placeholder="Filter by company name or stock ticker..."
        value={searchTerm}
        onChange={handleInputChange}
        className="w-full pl-10 pr-4 py-2.5 text-xs rounded-xl theme-input placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 transition-all duration-200"
      />
    </div>
  );
};

export default CompanySearch;
