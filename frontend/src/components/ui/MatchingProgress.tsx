import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Zap,
  Brain,
  Download,
  Search,
  Database,
  Sparkles,
  X,
  RotateCcw,
} from 'lucide-react';
import type { MatchingStatus } from '../../types';

interface MatchingProgressProps {
  status: MatchingStatus;
  onDismiss: () => void;
  onRetry: () => void;
}

const STAGES = [
  { key: 'initializing', label: 'Starting up', icon: Zap },
  { key: 'loading_model', label: 'Loading AI models', icon: Brain },
  { key: 'initial_fetch', label: 'Fetching new jobs', icon: Download },
  { key: 'fetching_jobs', label: 'Finding unmatched jobs', icon: Search },
  { key: 'semantic_filtering', label: 'Semantic matching', icon: Database },
  { key: 'saving_matches', label: 'Saving matches', icon: Database },
  { key: 'claude_analysis', label: 'AI deep analysis', icon: Sparkles },
  { key: 'done', label: 'Complete', icon: CheckCircle2 },
] as const;

function getStageIndex(stage?: string): number {
  if (!stage) return -1;
  return STAGES.findIndex((s) => s.key === stage);
}

export default function MatchingProgress({ status, onDismiss, onRetry }: MatchingProgressProps) {
  const isVisible = status.status === 'running' || status.status === 'completed' || status.status === 'error';
  const [autoDismissTimer, setAutoDismissTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [snippetIndex, setSnippetIndex] = useState(0);

  // Rotate news snippets every 15 seconds
  useEffect(() => {
    const snippets = status.news_snippets;
    if (status.status !== 'running' || !snippets || snippets.length <= 1) return;

    const interval = setInterval(() => {
      setSnippetIndex((prev) => (prev + 1) % snippets.length);
    }, 15000);

    return () => clearInterval(interval);
  }, [status.status, status.news_snippets]);

  // Reset snippet index when snippets array arrives
  useEffect(() => {
    setSnippetIndex(0);
  }, [status.news_snippets?.length]);

  // Auto-dismiss on completed (8s) or error (15s)
  useEffect(() => {
    if (autoDismissTimer) clearTimeout(autoDismissTimer);

    if (status.status === 'completed') {
      const timer = setTimeout(onDismiss, 8000);
      setAutoDismissTimer(timer);
      return () => clearTimeout(timer);
    }
    if (status.status === 'error') {
      const timer = setTimeout(onDismiss, 15000);
      setAutoDismissTimer(timer);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.status, onDismiss]);

  const currentStageIndex = getStageIndex(status.stage);

  // Skip initial_fetch stage if it doesn't appear (only on first run)
  const visibleStages = STAGES.filter((s) => {
    if (s.key === 'initial_fetch') {
      // Only show if the backend sent this stage
      return status.stage === 'initial_fetch' || currentStageIndex > getStageIndex('initial_fetch');
    }
    return true;
  });

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="mb-8"
        >
          <div className="border border-cyan-200 rounded-2xl bg-white shadow-sm overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-3">
              <div className="flex items-center gap-3">
                {status.status === 'running' && (
                  <Loader2 className="w-5 h-5 text-cyan-600 animate-spin" />
                )}
                {status.status === 'completed' && (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                )}
                {status.status === 'error' && (
                  <XCircle className="w-5 h-5 text-rose-500" />
                )}
                <h3 className="text-base font-semibold text-slate-900">
                  {status.status === 'running' && 'Matching in Progress'}
                  {status.status === 'completed' && 'Matching Complete!'}
                  {status.status === 'error' && 'Matching Failed'}
                </h3>
              </div>
              <button
                onClick={onDismiss}
                className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors rounded-lg hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Progress bar */}
            <div className="px-6 pb-3">
              <div className="w-full bg-slate-100 rounded-full h-2.5">
                <motion.div
                  className={`h-2.5 rounded-full ${
                    status.status === 'completed'
                      ? 'bg-emerald-500'
                      : status.status === 'error'
                      ? 'bg-rose-400'
                      : 'bg-gradient-to-r from-cyan-500 to-cyan-600'
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${status.progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <div className="flex items-center justify-between mt-1.5">
                <p className="text-sm text-slate-500">{status.message}</p>
                <span className="text-sm font-semibold text-cyan-600 tabular-nums">
                  {Math.round(status.progress)}%
                </span>
              </div>
            </div>

            {/* Stage timeline */}
            {status.status === 'running' && (
              <div className="px-6 pb-4">
                <div className="flex items-center gap-1 flex-wrap">
                  {visibleStages.map((stage, idx) => {
                    const stageIdx = getStageIndex(stage.key);
                    const isCompleted = stageIdx < currentStageIndex;
                    const isCurrent = stageIdx === currentStageIndex;
                    const Icon = stage.icon;

                    return (
                      <div key={stage.key} className="flex items-center gap-1">
                        <div
                          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                            isCompleted
                              ? 'bg-emerald-50 text-emerald-700'
                              : isCurrent
                              ? 'bg-cyan-50 text-cyan-700 ring-1 ring-cyan-200'
                              : 'bg-slate-50 text-slate-400'
                          }`}
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          ) : isCurrent ? (
                            <Loader2 className="w-3.5 h-3.5 text-cyan-600 animate-spin" />
                          ) : (
                            <Icon className="w-3.5 h-3.5" />
                          )}
                          <span className="hidden sm:inline">{stage.label}</span>
                        </div>
                        {idx < visibleStages.length - 1 && (
                          <div
                            className={`w-3 h-px ${
                              isCompleted ? 'bg-emerald-300' : 'bg-slate-200'
                            }`}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* News snippets (rotating every 15s) */}
            {status.status === 'running' && status.news_snippets && status.news_snippets.length > 0 && (
              <div className="px-6 pb-4">
                <div className="flex items-start gap-2.5 bg-cyan-50 rounded-xl px-4 py-3 min-h-[3.5rem]">
                  <Sparkles className="w-4 h-4 text-cyan-500 mt-0.5 flex-shrink-0" />
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={snippetIndex}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.3 }}
                      className="text-sm text-slate-600 leading-relaxed"
                    >
                      {status.news_snippets[snippetIndex]}
                    </motion.p>
                  </AnimatePresence>
                </div>
              </div>
            )}

            {/* Counters */}
            {(status.matches_found != null || status.jobs_analyzed != null || status.total_jobs != null) && status.status === 'running' && (
              <div className="px-6 pb-4 flex items-center gap-4 text-xs text-slate-500">
                {status.total_chunks != null && status.total_chunks > 1 && status.current_chunk != null && (
                  <span className="text-slate-700 font-medium">Chunk {status.current_chunk}/{status.total_chunks}</span>
                )}
                {status.total_jobs != null && (
                  <span>{status.total_jobs} jobs to process</span>
                )}
                {status.matches_found != null && status.matches_found > 0 && (
                  <span className="text-emerald-600 font-medium">{status.matches_found} matches found</span>
                )}
                {status.jobs_analyzed != null && status.jobs_analyzed > 0 && (
                  <span className="text-cyan-600 font-medium">{status.jobs_analyzed} analyzed by AI</span>
                )}
              </div>
            )}

            {/* Completed summary */}
            {status.status === 'completed' && (
              <div className="px-6 pb-5">
                <div className="flex items-center gap-4 text-sm">
                  {status.matches_found != null && (
                    <span className="text-emerald-600 font-medium">
                      {status.matches_found} matches found
                    </span>
                  )}
                  {status.jobs_analyzed != null && status.jobs_analyzed > 0 && (
                    <span className="text-cyan-600 font-medium">
                      {status.jobs_analyzed} analyzed by AI
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Error action */}
            {status.status === 'error' && (
              <div className="px-6 pb-5">
                <button
                  onClick={onRetry}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                  Try Again
                </button>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
