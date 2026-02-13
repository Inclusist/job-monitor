import { useQuery } from '@tanstack/react-query';
import { 
  Brain, 
  ThumbsUp, 
  ThumbsDown, 
  Target, 
  Zap, 
  History, 
  TrendingUp, 
  AlertCircle,
  Loader2,
  CheckCircle2,
  MessageSquare,
  BarChart3
} from 'lucide-react';
import { getLearningInsights } from '../services/jobs';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import ScoreDisplay from '../components/ui/ScoreDisplay';

export default function LearningInsightsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['learning-insights'],
    queryFn: getLearningInsights,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <Header />
        <main className="flex-grow flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-cyan-600 animate-spin mx-auto mb-4" />
            <p className="text-slate-600 font-medium">Analyzing your feedback history...</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (error || !data?.success) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <Header />
        <main className="flex-grow flex items-center justify-center p-6">
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 max-w-md w-full text-center">
            <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-slate-900 mb-2">Failed to load insights</h2>
            <p className="text-slate-600 mb-6">We couldn't retrieve your learning data. Please try again later.</p>
            <button 
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 bg-slate-900 text-white rounded-xl font-semibold hover:bg-slate-800 transition-colors"
            >
              Retry
            </button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const { ai_instructions, preferences, feedback_history } = data;

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      
      <main className="max-w-7xl mx-auto px-6 pt-32 pb-20">
        {/* Hero Section */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2 text-cyan-600 font-bold tracking-wider text-xs uppercase">
            <Brain className="w-4 h-4" />
            AI Training Lab
          </div>
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-4">
            Matching Insights & Learning
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
            See how the system adapts to your unique preferences. Every rating you give helps the AI calibrate its scoring to match your career goals.
          </p>
        </div>

        {!preferences.has_feedback ? (
          <div className="bg-white border border-cyan-100 rounded-3xl p-12 text-center shadow-sm">
            <div className="w-20 h-20 bg-cyan-50 rounded-full flex items-center justify-center mx-auto mb-6">
              <MessageSquare className="w-10 h-10 text-cyan-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-3">No feedback yet</h2>
            <p className="text-slate-600 max-w-lg mx-auto mb-8">
              Start rating job matches in your feed to train the AI. Your specific reasons help the system understand what matters to you most.
            </p>
            <a 
              href="/jobs"
              className="inline-flex items-center gap-2 px-8 py-3 bg-cyan-600 text-white rounded-2xl font-bold hover:bg-cyan-500 transition-all shadow-lg shadow-cyan-200"
            >
              Go to Job Feed
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: AI Instructions & Patterns */}
            <div className="lg:col-span-2 space-y-8">
              {/* AI Synthesized Instructions */}
              <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
                <div className="bg-slate-900 p-6 flex items-center justify-between">
                  <div className="flex items-center gap-3 text-white">
                    <Zap className="w-5 h-5 text-amber-400 fill-amber-400" />
                    <h3 className="font-bold text-lg tracking-tight text-white">Active Scoring Instructions</h3>
                  </div>
                  <div className="px-3 py-1 bg-white/10 rounded-full text-[10px] font-bold text-white uppercase tracking-widest border border-white/20">
                    Live Engine State
                  </div>
                </div>
                <div className="p-8">
                  {typeof ai_instructions === 'string' && ai_instructions ? (
                    <div className="space-y-4">
                      {ai_instructions.split('\n').filter(line => line.trim().startsWith('-')).map((instruction, i) => (
                        <div key={i} className="flex items-start gap-4 p-4 bg-slate-50 border border-slate-100 rounded-2xl group hover:border-cyan-200 hover:bg-cyan-50/30 transition-all">
                          <div className="mt-1 w-5 h-5 bg-cyan-100 text-cyan-600 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">
                            {i + 1}
                          </div>
                          <p className="text-slate-700 leading-relaxed font-medium group-hover:text-slate-900 transition-colors">
                            {instruction.replace('-', '').trim()}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-10 text-center text-slate-400">
                      <p>AI is synthesizing instructions from your data...</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Statistical Preferences */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
                      <ThumbsUp className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-slate-900">Valued Aspects</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {preferences.key_preferences.valued_aspects.map((aspect, i) => (
                      <span key={i} className="px-4 py-2 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full text-sm font-semibold capitalize">
                        {aspect}
                      </span>
                    ))}
                    {preferences.key_preferences.valued_aspects.length === 0 && (
                      <p className="text-slate-400 text-sm italic">Analyzing your positive feedback...</p>
                    )}
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-rose-50 text-rose-600 rounded-xl">
                      <ThumbsDown className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-slate-900">Dealbreakers</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {preferences.key_preferences.dealbreakers.map((aspect, i) => (
                      <span key={i} className="px-4 py-2 bg-rose-50 text-rose-700 border border-rose-100 rounded-full text-sm font-semibold capitalize">
                        {aspect}
                      </span>
                    ))}
                    {preferences.key_preferences.dealbreakers.length === 0 && (
                      <p className="text-slate-400 text-sm italic">Analyzing your negative feedback...</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Recent Feedback History */}
              <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 text-slate-600 rounded-xl">
                      <History className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-slate-900 text-lg tracking-tight">Feedback History</h3>
                  </div>
                  <div className="text-sm font-medium text-slate-400">
                    Last {feedback_history.length} interactions
                  </div>
                </div>

                <div className="space-y-4">
                  {feedback_history.map((fb, i) => (
                    <div key={i} className="flex items-center justify-between p-4 border border-slate-100 rounded-2xl hover:border-slate-200 transition-all">
                      <div className="flex-grow min-w-0 pr-4">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full ${
                            fb.feedback_type === 'agree' ? 'bg-emerald-500' :
                            fb.feedback_type === 'disagree' ? 'bg-rose-500' :
                            'bg-amber-500'
                          }`} />
                          <h4 className="font-bold text-slate-900 truncate">{fb.title}</h4>
                        </div>
                        <p className="text-xs text-slate-500 truncate mb-2">{fb.company}</p>
                        {fb.feedback_reason && (
                          <div className="flex items-start gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-100 italic text-xs text-slate-600">
                            <MessageSquare className="w-3 h-3 mt-0.5 shrink-0" />
                            "{fb.feedback_reason}"
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        <div className="text-right">
                          <div className="text-[10px] uppercase font-bold text-slate-400 leading-none mb-1">Scores</div>
                          <div className="flex items-center gap-2 text-sm">
                            <span className="font-bold text-slate-400">{fb.match_score_original}</span>
                            <span className="text-slate-300">→</span>
                            <span className="font-bold text-cyan-600">{fb.match_score_user || fb.match_score_original}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: Stats & Calibration */}
            <div className="space-y-8">
              {/* Calibration Card */}
              <div className="bg-gradient-to-br from-cyan-600 to-cyan-700 rounded-3xl p-8 shadow-xl shadow-cyan-200 text-white relative overflow-hidden">
                <Target className="absolute top-[-20px] right-[-20px] w-40 h-40 text-white/5 rotate-12" />
                
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-cyan-200" />
                  Scoring Calibration
                </h3>

                <div className="grid grid-cols-2 gap-4 mb-8">
                  <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10">
                    <div className="text-[10px] uppercase font-bold text-cyan-100 mb-1">AI Avg</div>
                    <div className="text-3xl font-black">{Math.round(preferences.scoring_calibration.avg_original_score)}</div>
                  </div>
                  <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10">
                    <div className="text-[10px] uppercase font-bold text-cyan-100 mb-1">Your Avg</div>
                    <div className="text-3xl font-black">{Math.round(preferences.scoring_calibration.avg_user_score)}</div>
                  </div>
                </div>

                <div className="space-y-4 relative z-10">
                  <div className="flex items-center justify-between text-sm font-medium">
                    <span>Agreement Rate</span>
                    <span>{preferences.agreement_rate.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-white/20 rounded-full h-2">
                    <div 
                      className="bg-white rounded-full h-2 transition-all duration-1000" 
                      style={{ width: `${preferences.agreement_rate}%` }}
                    />
                  </div>
                  
                  <div className="pt-4 border-t border-white/10 mt-4">
                    <p className="text-xs leading-relaxed text-cyan-50 italic">
                      {preferences.scoring_calibration.needs_calibration 
                        ? `AI has noticed it scores ~${Math.abs(Math.round(preferences.scoring_calibration.score_bias))} points ${preferences.scoring_calibration.score_bias > 0 ? 'higher' : 'lower'} than you. It is automatically adjusting its logic for future matches.`
                        : "Your scoring expectations are perfectly aligned with the AI engine. No major calibration needed."}
                    </p>
                  </div>
                </div>
              </div>

              {/* Stats Summary */}
              <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
                <h3 className="font-bold text-slate-900 mb-6">Learning Metrics</h3>
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <span className="text-sm font-semibold text-slate-600">Total Feedback</span>
                    </div>
                    <span className="text-lg font-bold text-slate-900">{preferences.total_feedback}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <span className="text-sm font-semibold text-slate-600">Perfect Matches</span>
                    </div>
                    <span className="text-lg font-bold text-slate-900">
                      {feedback_history.filter(f => f.feedback_type === 'agree').length}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-amber-50 text-amber-600 rounded-xl">
                        <TrendingUp className="w-4 h-4" />
                      </div>
                      <span className="text-sm font-semibold text-slate-600">Growth Score</span>
                    </div>
                    <span className="text-lg font-bold text-slate-900">
                      {Math.min(100, preferences.total_feedback * 5)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Tips Card */}
              <div className="p-8 bg-cyan-50 border border-cyan-100 rounded-3xl">
                <h4 className="font-bold text-cyan-900 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Pro-Tip
                </h4>
                <p className="text-sm text-cyan-800 leading-relaxed italic">
                  "When you rate a match as 'Too High' or 'Too Low', always try to add a specific reason. This is the single most powerful signal for the matching engine."
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}