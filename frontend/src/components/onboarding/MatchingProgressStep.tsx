import { useState, useEffect } from 'react';
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
    ArrowRight,
    RotateCcw,
} from 'lucide-react';
import { runMatching, getMatchingStatus } from '../../services/matching';
import type { MatchingStatus } from '../../types';

interface MatchingProgressStepProps {
    onNext: () => void;
    onBack?: () => void;
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

const STAGE_EXPLANATIONS: Record<string, string> = {
    initializing: 'Setting up your profile and preparing search parameters based on your preferences.',
    loading_model: 'Loading the AI embedding model that understands job descriptions and your skills at a semantic level.',
    initial_fetch: 'Pulling the latest job postings from our sources into the database.',
    fetching_jobs: 'Identifying jobs in your preferred locations that haven\'t been matched against your profile yet.',
    semantic_filtering: 'Computing how closely each job\'s requirements align with your skills and experience using vector similarity.',
    saving_matches: 'Persisting the semantic match scores so you can browse and filter your results.',
    claude_analysis: 'Running a deep AI review on your top matches — scoring fit, highlighting alignments, and flagging gaps.',
    done: 'All done! Your matched jobs are ready to review.',
};

function getStageIndex(stage?: string): number {
    if (!stage) return -1;
    return STAGES.findIndex((s) => s.key === stage);
}

export default function MatchingProgressStep({ onNext }: MatchingProgressStepProps) {
    const [status, setStatus] = useState<MatchingStatus>({
        status: 'idle',
        progress: 0,
        message: 'Preparing to find your matches...',
    });
    const [error, setError] = useState<string | null>(null);
    const [snippetIndex, setSnippetIndex] = useState(0);

    useEffect(() => {
        startMatching();
        const interval = setInterval(pollStatus, 2000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

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

    const startMatching = async () => {
        setError(null);
        try {
            await runMatching(true);
            pollStatus();
        } catch (err) {
            console.error('Error starting matching:', err);
            setError('Failed to start matching. Please try again.');
        }
    };

    const pollStatus = async () => {
        try {
            const currentStatus = await getMatchingStatus();
            setStatus(currentStatus);

            if (currentStatus.status === 'error') {
                setError(currentStatus.message || 'Matching failed. Please try again.');
            }
        } catch (err) {
            console.error('Error polling matching status:', err);
        }
    };

    const isComplete = status.status === 'completed' || status.progress === 100;
    const currentStageIndex = getStageIndex(status.stage);

    // Skip initial_fetch stage if it doesn't appear (only on first run)
    const visibleStages = STAGES.filter((s) => {
        if (s.key === 'initial_fetch') {
            return status.stage === 'initial_fetch' || currentStageIndex > getStageIndex('initial_fetch');
        }
        return true;
    });

    const currentExplanation = STAGE_EXPLANATIONS[status.stage || 'initializing'] || STAGE_EXPLANATIONS.initializing;

    return (
        <div className="max-w-2xl mx-auto text-center">
            <div className="mb-10">
                <h2 className="text-3xl font-bold text-slate-900 mb-4">
                    Finding Your Perfect Matches
                </h2>
                <p className="text-lg text-slate-600">
                    We're running our AI matching engine to find the best opportunities for you.
                </p>
            </div>

            <div className="border border-cyan-200 rounded-2xl bg-white shadow-sm overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-center gap-3 px-6 pt-5 pb-3">
                    {status.status === 'running' && (
                        <Loader2 className="w-5 h-5 text-cyan-600 animate-spin" />
                    )}
                    {isComplete && (
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    )}
                    {status.status === 'error' && (
                        <XCircle className="w-5 h-5 text-rose-500" />
                    )}
                    <h3 className="text-base font-semibold text-slate-900">
                        {status.status === 'running' && 'Matching in Progress'}
                        {isComplete && 'Matching Complete!'}
                        {status.status === 'error' && 'Matching Failed'}
                        {status.status === 'idle' && 'Starting...'}
                    </h3>
                </div>

                {/* Progress bar */}
                <div className="px-6 pb-3">
                    <div className="w-full bg-slate-100 rounded-full h-2.5">
                        <motion.div
                            className={`h-2.5 rounded-full ${
                                isComplete
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
                        <div className="flex items-center gap-1 flex-wrap justify-center">
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

                {/* Stage explanation */}
                {status.status === 'running' && (
                    <div className="px-6 pb-4">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={status.stage}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -6 }}
                                transition={{ duration: 0.25 }}
                                className="flex items-start gap-2.5 bg-cyan-50 rounded-xl px-4 py-3"
                            >
                                <Sparkles className="w-4 h-4 text-cyan-500 mt-0.5 flex-shrink-0" />
                                <p className="text-sm text-slate-600 leading-relaxed text-left">
                                    {currentExplanation}
                                </p>
                            </motion.div>
                        </AnimatePresence>
                    </div>
                )}

                {/* News snippets (rotating every 15s) */}
                {status.status === 'running' && status.news_snippets && status.news_snippets.length > 0 && (
                    <div className="px-6 pb-4">
                        <div className="flex items-start gap-2.5 bg-slate-50 rounded-xl px-4 py-3 min-h-[3.5rem]">
                            <Sparkles className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                            <AnimatePresence mode="wait">
                                <motion.p
                                    key={snippetIndex}
                                    initial={{ opacity: 0, y: 4 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -4 }}
                                    transition={{ duration: 0.3 }}
                                    className="text-sm text-slate-500 leading-relaxed text-left"
                                >
                                    {status.news_snippets[snippetIndex]}
                                </motion.p>
                            </AnimatePresence>
                        </div>
                    </div>
                )}

                {/* Counters */}
                {(status.matches_found != null || status.jobs_analyzed != null || status.total_jobs != null) && status.status === 'running' && (
                    <div className="px-6 pb-4 flex items-center justify-center gap-4 text-xs text-slate-500">
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

                {/* Completed summary + CTA */}
                {isComplete && (
                    <div className="px-6 pb-6">
                        <div className="flex items-center justify-center gap-4 text-sm mb-6">
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

                        <button
                            onClick={onNext}
                            className="w-full py-4 bg-cyan-600 text-white rounded-xl font-bold text-lg hover:bg-cyan-700 transition-all flex items-center justify-center gap-2 group shadow-lg shadow-cyan-200"
                        >
                            <span>See My Results</span>
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                )}

                {/* Error action */}
                {error && !isComplete && (
                    <div className="px-6 pb-6">
                        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-red-700 mb-4">
                            <p>{error}</p>
                        </div>
                        <button
                            onClick={startMatching}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors"
                        >
                            <RotateCcw className="w-4 h-4" />
                            Try Again
                        </button>
                    </div>
                )}
            </div>

            <div className="mt-8">
                <p className="text-sm text-slate-400">
                    Your first results are based on the latest available jobs in our database for maximum speed.
                    You can run a deeper search anytime once you're inside.
                </p>
            </div>
        </div>
    );
}
