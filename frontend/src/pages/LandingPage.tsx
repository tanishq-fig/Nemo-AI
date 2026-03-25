import React from 'react';
import { Link } from 'react-router-dom';
import { Waves, MessageCircle, Map, BarChart3, ArrowRight } from 'lucide-react';

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Hero */}
      <section className="min-h-[85vh] flex items-center justify-center px-4">
        <div className="text-center max-w-2xl space-y-6">
          <Waves className="w-14 h-14 mx-auto text-cyan-400" />
          <h1 className="text-5xl font-bold tracking-tight">
            ARGO Intelligence
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed">
            AI-powered platform for exploring oceanographic data — temperature,
            salinity, and float trajectories at your fingertips.
          </p>
          <div className="flex gap-3 justify-center pt-2">
            <Link
              to="/register"
              className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              Get started <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/login"
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors border border-white/10"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 border-t border-white/5">
        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
          {[
            { icon: <MessageCircle className="w-6 h-6" />, title: 'AI Chat', desc: 'Ask natural language questions about ocean data and get instant insights.' },
            { icon: <Map className="w-6 h-6" />, title: 'Interactive Maps', desc: 'Explore global float positions with temperature-coded markers.' },
            { icon: <BarChart3 className="w-6 h-6" />, title: 'Analytics', desc: 'Histograms, T-S diagrams, depth profiles, and statistical summaries.' },
          ].map((f) => (
            <div key={f.title} className="bg-slate-900/60 border border-white/5 rounded-xl p-5 space-y-3">
              <span className="text-cyan-400">{f.icon}</span>
              <h3 className="font-semibold">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-4 border-t border-white/5 text-center text-xs text-slate-600">
        &copy; 2026 ARGO Intelligence
      </footer>
    </div>
  );
};

export default LandingPage;
