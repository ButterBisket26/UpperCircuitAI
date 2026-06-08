import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Chat } from './pages/Chat';
import { Explorer } from './pages/Explorer';
import { Compare } from './pages/Compare';

function App() {
  const [activePage, setActivePage] = useState('chat');
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <div className={`min-h-screen flex flex-col select-text theme-bg ${theme}`}>
      {/* Dynamic Navigation Header */}
      <Navbar 
        activePage={activePage} 
        setActivePage={setActivePage} 
        theme={theme} 
        toggleTheme={toggleTheme} 
      />
      
      {/* Page Content Renderer */}
      <main className="flex-1 overflow-hidden">
        {activePage === 'chat' && <Chat />}
        {activePage === 'explorer' && <Explorer />}
        {activePage === 'compare' && <Compare />}
      </main>
    </div>
  );
}

export default App;
