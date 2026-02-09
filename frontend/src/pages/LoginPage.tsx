import { motion } from 'framer-motion';
import { Target, Shield, Sparkles, BarChart3 } from 'lucide-react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getGoogleLoginUrl, getLinkedInLoginUrl } from '../services/auth';

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="w-10 h-10 border-4 border-cyan-200 border-t-cyan-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/jobs" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left: Cyan gradient hero */}
      <motion.div
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8 }}
        className="lg:w-1/2 bg-gradient-to-br from-cyan-600 to-cyan-700 p-12 lg:p-16 flex flex-col justify-center relative overflow-hidden"
      >
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full mix-blend-screen blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full mix-blend-screen blur-3xl" />
        </div>

        <div className="relative z-10 max-w-md mx-auto lg:mx-0">
          <Link to="/" className="flex items-center space-x-2 mb-12">
            <Target className="w-7 h-7 text-white" strokeWidth={1.5} />
            <span className="text-2xl font-semibold text-white tracking-tight">Inclusist</span>
          </Link>

          <h1 className="text-3xl lg:text-4xl font-bold text-white mb-4 leading-tight">
            Find work that matches your skills.
          </h1>
          <p className="text-cyan-100 text-lg mb-12 leading-relaxed">
            AI-powered job matching that understands what you bring to the table.
          </p>

          <div className="space-y-6">
            {[
              { icon: Sparkles, text: 'Deep competency matching, not keyword spam' },
              { icon: BarChart3, text: 'Smart dashboard to track all your applications' },
              { icon: Shield, text: 'Fresh jobs daily, zero noise' },
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.4 + i * 0.15 }}
                className="flex items-center space-x-3"
              >
                <div className="w-9 h-9 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-5 h-5 text-white" strokeWidth={1.5} />
                </div>
                <span className="text-cyan-50 text-sm font-medium">{feature.text}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Right: OAuth buttons */}
      <motion.div
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="lg:w-1/2 flex items-center justify-center p-12 lg:p-16 bg-white"
      >
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome</h2>
          <p className="text-slate-500 mb-10">Sign in to access your matched jobs.</p>

          <div className="space-y-4">
            <a
              href={getGoogleLoginUrl()}
              className="w-full flex items-center justify-center gap-3 px-6 py-3.5 border border-slate-200 rounded-xl text-slate-700 font-medium hover:bg-slate-50 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Continue with Google
            </a>

            <a
              href={getLinkedInLoginUrl()}
              className="w-full flex items-center justify-center gap-3 px-6 py-3.5 border border-slate-200 rounded-xl text-slate-700 font-medium hover:bg-slate-50 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#0A66C2">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
              Continue with LinkedIn
            </a>
          </div>

          <div className="mt-10 flex items-center justify-center gap-2 text-xs text-slate-400">
            <Shield className="w-3.5 h-3.5" />
            <span>Your data is secure and never shared.</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
