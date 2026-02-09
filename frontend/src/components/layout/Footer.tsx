import { Target } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="py-12 px-6 border-t border-cyan-100">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <Link to="/" className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-cyan-600" strokeWidth={1.5} />
          <span className="text-lg font-semibold text-slate-900">Inclusist</span>
        </Link>
        <p className="text-sm text-slate-600">
          &copy; 2024 Inclusist. Built for clarity, not chaos.
        </p>
        <div className="flex items-center space-x-6">
          <a href="#" className="text-sm text-slate-600 hover:text-cyan-600 transition-colors">Privacy</a>
          <a href="#" className="text-sm text-slate-600 hover:text-cyan-600 transition-colors">Terms</a>
          <a href="#" className="text-sm text-slate-600 hover:text-cyan-600 transition-colors">Contact</a>
        </div>
      </div>
    </footer>
  );
}
