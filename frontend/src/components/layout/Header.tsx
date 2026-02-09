import { motion } from 'framer-motion';
import { Target, LogOut } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getLogoutUrl } from '../../services/auth';

export default function Header() {
  const { user, isAuthenticated } = useAuth();

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-cyan-100"
    >
      <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center space-x-2">
          <Target className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
          <span className="text-xl font-semibold text-slate-900 tracking-tight">Inclusist</span>
        </Link>

        <nav className="hidden md:flex items-center space-x-8">
          {isAuthenticated ? (
            <>
              <Link
                to="/jobs"
                className="text-slate-600 hover:text-cyan-600 transition-colors text-sm font-medium"
              >
                Jobs
              </Link>
              <div className="flex items-center space-x-3">
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name}
                    className="w-8 h-8 rounded-full"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-cyan-100 flex items-center justify-center text-cyan-700 text-sm font-semibold">
                    {user?.name?.charAt(0) || '?'}
                  </div>
                )}
                <span className="text-sm text-slate-700 font-medium">{user?.name}</span>
              </div>
              <a
                href={getLogoutUrl()}
                className="flex items-center space-x-1 text-slate-500 hover:text-slate-700 transition-colors text-sm"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </a>
            </>
          ) : (
            <>
              <a
                href="#how-it-works"
                className="text-slate-600 hover:text-cyan-600 transition-colors text-sm font-medium"
              >
                How it Works
              </a>
              <a
                href="#quality"
                className="text-slate-600 hover:text-cyan-600 transition-colors text-sm font-medium"
              >
                Philosophy
              </a>
              <Link
                to="/login"
                className="px-5 py-2.5 bg-cyan-600 text-white text-sm font-medium rounded-lg hover:bg-cyan-700 transition-colors"
              >
                Login
              </Link>
            </>
          )}
        </nav>
      </div>
    </motion.header>
  );
}
