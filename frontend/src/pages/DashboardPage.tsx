import React, { useState } from 'react';
import { LogOut, Map, MessageCircle, BarChart2, Waves } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ChatPanel } from '../components/ChatPanel';
import { OceanMap } from '../components/OceanMap';
import { VisualizationPanel } from '../components/VisualizationPanel';

type Tab = 'explore' | 'chat' | 'analytics';

const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'explore', label: 'Explore', icon: <Map className="w-4 h-4" /> },
  { id: 'chat', label: 'AI Chat', icon: <MessageCircle className="w-4 h-4" /> },
  { id: 'analytics', label: 'Analytics', icon: <BarChart2 className="w-4 h-4" /> },
];

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>('explore');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-white/10 bg-slate-900/80 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Waves className="w-7 h-7 text-cyan-400" />
          <span className="text-lg font-semibold tracking-tight">ARGO Intelligence</span>
        </div>

        {/* Tab bar */}
        <nav className="hidden sm:flex items-center bg-slate-800/60 rounded-full p-1 gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all
                ${activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-300'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400 hidden md:inline">{user?.name}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* Mobile tab bar */}
      <div className="sm:hidden flex border-b border-white/10 bg-slate-900/60">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all
              ${activeTab === tab.id
                ? 'text-cyan-300 border-b-2 border-cyan-400'
                : 'text-slate-500'
              }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content — ChatPanel stays mounted so messages persist across tab switches */}
      <main className="flex-1 overflow-hidden relative">
        <div className={activeTab === 'explore' ? 'h-full' : 'hidden'}><OceanMap /></div>
        <div className={activeTab === 'chat' ? 'h-full' : 'hidden'}><ChatPanel /></div>
        <div className={activeTab === 'analytics' ? 'h-full' : 'hidden'}><VisualizationPanel /></div>
      </main>
    </div>
  );
};

export default DashboardPage;
