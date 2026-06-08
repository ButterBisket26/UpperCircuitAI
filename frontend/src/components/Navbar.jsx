import React from 'react';
import { Sun, Moon } from 'lucide-react';

export const Navbar = ({ activePage, setActivePage, theme, toggleTheme }) => {
  const navigationItems = [
    { id: 'chat', label: 'Chat Q&A', icon: '💬' },
    { id: 'explorer', label: 'Filing Explorer', icon: '📂' },
    { id: 'compare', label: 'Compare Insights', icon: '📊' }
  ];

  return (
    <header className="sticky top-0 z-50 border-b theme-nav backdrop-blur-md px-6 py-4 flex items-center justify-between">
      {/* Brand Logo */}
      <div 
        onClick={() => setActivePage('chat')}
        className="flex items-center gap-3 cursor-pointer select-none group"
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/10 group-hover:scale-105 transition-transform duration-300">
          <span className="text-xl">📈</span>
        </div>
        <div>
          <span className="text-lg font-bold font-display tracking-tight theme-text-primary group-hover:text-blue-400 transition-colors duration-300">
            UpperCircuit<span className="text-blue-500">AI</span>
          </span>
          <div className="text-[10px] theme-text-muted font-medium font-mono uppercase tracking-widest leading-none mt-0.5">
            Indian Filing RAG
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <nav className="flex items-center gap-2">
        {navigationItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
              activePage === item.id
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-indigo-500/20 scale-[1.02]'
                : 'theme-text-secondary theme-bg-btn-hover'
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="ml-2 p-2.5 rounded-xl border border-transparent text-slate-400 hover:text-slate-200 transition-colors duration-300 theme-bg-btn-hover theme-text-secondary flex items-center justify-center"
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </nav>
    </header>
  );
};

export default Navbar;
