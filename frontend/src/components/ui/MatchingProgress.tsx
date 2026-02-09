import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import type { MatchingStatus } from '../../types';

interface MatchingProgressProps {
  status: MatchingStatus;
}

export default function MatchingProgress({ status }: MatchingProgressProps) {
  const isRunning = status.status === 'running';

  return (
    <AnimatePresence>
      {isRunning && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="bg-white rounded-2xl p-8 shadow-xl max-w-md w-full mx-4 border border-cyan-200"
          >
            <div className="flex items-center gap-3 mb-6">
              <Loader2 className="w-6 h-6 text-cyan-600 animate-spin" />
              <h3 className="text-lg font-semibold text-slate-900">
                Matching in Progress
              </h3>
            </div>

            <div className="w-full bg-slate-100 rounded-full h-3 mb-3">
              <motion.div
                className="bg-gradient-to-r from-cyan-500 to-cyan-600 h-3 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${status.progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>

            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-600">{status.message}</p>
              <span className="text-sm font-semibold text-cyan-600 tabular-nums">
                {Math.round(status.progress)}%
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
