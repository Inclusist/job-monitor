import { useState, useCallback } from 'react';
import {
  ExternalLink,
  MapPin,
  Building2,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Briefcase,
  GraduationCap,
  Wifi,
  Clock,
  DollarSign,
  Loader2,
  AlertCircle,
  Check,
  FileText,
  Mail,
  LayoutDashboard,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
} from 'lucide-react';
import Badge from './ui/Badge';
import ScoreDisplay from './ui/ScoreDisplay';
import ResumeModal from './ResumeModal';
import CoverLetterModal from './CoverLetterModal';
import { useJobDetail } from '../hooks/useJobDetail';
import { claimItems, shortlistJob, removeShortlist, analyzeJob, submitFeedback } from '../services/jobs';
import { useQueryClient, useMutation } from '@tanstack/react-query';

interface JobDetailPanelProps {
  jobId: number;
}

export default function JobDetailPanel({ jobId }: JobDetailPanelProps) {
  const { data: job, isLoading, error } = useJobDetail(jobId);
  const queryClient = useQueryClient();

  // Track items the user has just claimed in this session (optimistic UI)
  const [newlyClaimed, setNewlyClaimed] = useState<Set<string>>(new Set());
  const [claimingItem, setClaimingItem] = useState<string | null>(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [showCoverLetterModal, setShowCoverLetterModal] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'agree' | 'disagree' | 'too_high' | 'too_low' | null>(null);
  const [feedbackReason, setFeedbackReason] = useState('');
  const [userScore, setUserScore] = useState<number | ''>('');

  const DASHBOARD_STATUSES = ['shortlisted', 'applied', 'interviewing', 'offered'];
  const isOnDashboard = job ? DASHBOARD_STATUSES.includes(job.status ?? '') : false;

  const dashboardMutation = useMutation({
    mutationFn: () => {
      if (!job) return Promise.resolve({ success: true });
      return isOnDashboard ? removeShortlist(job.id) : shortlistJob(job.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobDetail', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobDetail', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: (feedbackData: {
      feedback_type: 'agree' | 'disagree' | 'too_high' | 'too_low';
      match_score_original: number;
      feedback_reason?: string;
    }) => submitFeedback(jobId, feedbackData),
    onSuccess: () => {
      setFeedbackSubmitted(true);
      setTimeout(() => setFeedbackSubmitted(false), 3000);
    },
  });

  const handleClaim = useCallback(async (name: string, type: 'competency' | 'skill') => {
    const key = `${type}:${name}`;
    if (newlyClaimed.has(key)) return;

    setClaimingItem(key);
    // Optimistic: show claimed immediately
    setNewlyClaimed((prev) => new Set(prev).add(key));
    try {
      await claimItems([{ name, type }]);
      // Invalidate so re-opening will show updated claimed state from backend
      queryClient.invalidateQueries({ queryKey: ['jobDetail', jobId] });
    } catch (err) {
      // Revert optimistic update on failure
      setNewlyClaimed((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
      console.error('Failed to claim item:', err);
    } finally {
      setClaimingItem(null);
    }
  }, [newlyClaimed, jobId, queryClient]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500">
        <AlertCircle className="w-8 h-8 mb-2" />
        <p>Failed to load job details.</p>
      </div>
    );
  }

  const claimedCompSet = new Set(job.claimed_competency_names.map((n) => n.toLowerCase()));
  const claimedSkillSet = new Set(job.claimed_skill_names.map((n) => n.toLowerCase()));

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-xl font-bold text-slate-900">{job.title}</h3>
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 p-2 text-slate-400 hover:text-cyan-600 transition-colors rounded-lg hover:bg-cyan-50"
              title="Open job posting"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-slate-500">
          {job.company && (
            <span className="flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5" />
              {job.company}
            </span>
          )}
          {job.location && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {job.location}
            </span>
          )}
          {job.posted_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {new Date(job.posted_date).toLocaleDateString()}
            </span>
          )}
          {job.source && (
            <span className="text-slate-400">{job.source}</span>
          )}
        </div>
        {(job.priority || (job.status && job.status !== 'new')) && (
          <div className="flex items-center gap-2 mt-3">
            {job.priority && <Badge type="priority" value={job.priority} />}
            {job.status && job.status !== 'new' && <Badge type="status" value={job.status} />}
          </div>
        )}
      </div>

      {/* Score */}
      {job.claude_score != null && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
            <div className="flex items-center gap-4">
              <ScoreDisplay score={job.claude_score} label="AI Match" />
              <button
                onClick={() => analyzeMutation.mutate()}
                disabled={analyzeMutation.isPending}
                className="p-2 text-slate-400 hover:text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors"
                title="Re-run analysis with current learnings"
              >
                {analyzeMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )}
              </button>
            </div>
            
            <div className="flex flex-col items-end gap-2">
              <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400">Rate Match</span>
              <div className="flex items-center gap-1.5">
                {feedbackSubmitted ? (
                  <span className="text-xs font-medium text-emerald-600 flex items-center gap-1">
                    <Check className="w-3 h-3" /> Thanks!
                  </span>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setFeedbackType('agree');
                        setShowFeedbackForm(true);
                      }}
                      disabled={feedbackMutation.isPending}
                      className={`p-2 rounded-lg transition-colors ${
                        feedbackType === 'agree' ? 'text-emerald-600 bg-emerald-50' : 'text-slate-400 hover:text-emerald-600 hover:bg-emerald-50'
                      }`}
                      title="Score is accurate"
                    >
                      <ThumbsUp className="w-4 h-4" />
                    </button>
                    <div className="w-px h-4 bg-slate-200" />
                    <button
                      onClick={() => {
                        setFeedbackType('too_high');
                        setShowFeedbackForm(true);
                      }}
                      disabled={feedbackMutation.isPending}
                      className={`p-2 rounded-lg transition-colors ${
                        feedbackType === 'too_high' ? 'text-amber-600 bg-amber-50' : 'text-slate-400 hover:text-amber-600 hover:bg-amber-50'
                      }`}
                      title="Score is too high"
                    >
                      <span className="text-[10px] font-bold">HIGH</span>
                    </button>
                    <button
                      onClick={() => {
                        setFeedbackType('too_low');
                        setShowFeedbackForm(true);
                      }}
                      disabled={feedbackMutation.isPending}
                      className={`p-2 rounded-lg transition-colors ${
                        feedbackType === 'too_low' ? 'text-blue-600 bg-blue-50' : 'text-slate-400 hover:text-blue-600 hover:bg-blue-50'
                      }`}
                      title="Score is too low"
                    >
                      <span className="text-[10px] font-bold">LOW</span>
                    </button>
                    <button
                      onClick={() => {
                        setFeedbackType('disagree');
                        setShowFeedbackForm(true);
                      }}
                      disabled={feedbackMutation.isPending}
                      className={`p-2 rounded-lg transition-colors ${
                        feedbackType === 'disagree' ? 'text-rose-600 bg-rose-50' : 'text-slate-400 hover:text-rose-600 hover:bg-rose-50'
                      }`}
                      title="Score is incorrect"
                    >
                      <ThumbsDown className="w-4 h-4" />
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {showFeedbackForm && !feedbackSubmitted && (
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm animate-in slide-in-from-top-2 duration-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-slate-900">Provide Feedback</h4>
                <button 
                  onClick={() => setShowFeedbackForm(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <AlertCircle className="w-4 h-4" rotate={45} />
                </button>
              </div>

              <div className="space-y-4">
                {feedbackType !== 'agree' && (
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                      What score would you give? (0-100)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={userScore}
                      onChange={(e) => setUserScore(e.target.value ? parseInt(e.target.value) : '')}
                      placeholder="e.g. 85"
                      className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:bg-white transition-all"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
                    {feedbackType === 'agree' ? 'Why is this a good match?' : 'What did the AI miss?'}
                  </label>
                  <textarea
                    value={feedbackReason}
                    onChange={(e) => setFeedbackReason(e.target.value)}
                    placeholder={feedbackType === 'agree' 
                      ? "e.g. Perfect seniority and domain match..." 
                      : "e.g. Too much travel required, or missing leadership experience..."
                    }
                    rows={3}
                    className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:bg-white transition-all resize-none"
                  />
                  <p className="mt-1.5 text-[10px] text-slate-400 italic">
                    💡 Specific reasons help the AI learn your preferences better.
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      feedbackMutation.mutate({
                        feedback_type: feedbackType!,
                        match_score_original: job.claude_score!,
                        match_score_user: typeof userScore === 'number' ? userScore : undefined,
                        feedback_reason: feedbackReason
                      });
                      setShowFeedbackForm(false);
                      setFeedbackReason('');
                      setUserScore('');
                    }}
                    disabled={feedbackMutation.isPending}
                    className="flex-1 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                  >
                    {feedbackMutation.isPending ? 'Submitting...' : 'Submit Feedback'}
                  </button>
                  <button
                    onClick={() => setShowFeedbackForm(false)}
                    className="px-4 py-2 bg-slate-100 text-slate-600 text-xs font-bold rounded-lg hover:bg-slate-200 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Analyze button when no Claude score */}
      {job.claude_score == null && (
        <button
          onClick={() => analyzeMutation.mutate()}
          disabled={analyzeMutation.isPending}
          className="w-full px-4 py-2.5 text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 bg-cyan-50 text-cyan-700 border border-cyan-200 hover:bg-cyan-100 disabled:opacity-50"
        >
          {analyzeMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4" />
          )}
          Run AI Analysis
        </button>
      )}

      {/* Generate Resume / Cover Letter */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowResumeModal(true)}
          className="flex-1 px-4 py-2.5 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors flex items-center justify-center gap-2"
        >
          <FileText className="w-4 h-4" />
          Generate Resume
        </button>
        <button
          onClick={() => setShowCoverLetterModal(true)}
          className="flex-1 px-4 py-2.5 border border-cyan-200 text-cyan-600 text-sm font-semibold rounded-xl hover:bg-cyan-50 transition-colors flex items-center justify-center gap-2"
        >
          <Mail className="w-4 h-4" />
          Generate Cover Letter
        </button>
      </div>

      {/* Add to Dashboard */}
      <button
        onClick={() => dashboardMutation.mutate()}
        disabled={dashboardMutation.isPending}
        className={`w-full px-4 py-2.5 text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 ${
          isOnDashboard
            ? 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
            : 'bg-slate-100 text-slate-700 border border-slate-200 hover:bg-cyan-50 hover:text-cyan-700 hover:border-cyan-200'
        } disabled:opacity-50`}
      >
        {dashboardMutation.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <LayoutDashboard className="w-4 h-4" />
        )}
        {isOnDashboard ? 'On Dashboard' : 'Add to Dashboard'}
      </button>

      {/* Metadata pills */}
      {(job.ai_experience_level || job.ai_work_arrangement || job.ai_employment_type || job.salary) && (
        <div className="flex flex-wrap gap-2">
          {job.ai_experience_level && (
            <MetadataPill icon={<GraduationCap className="w-3.5 h-3.5" />} label={`Exp: ${job.ai_experience_level}`} />
          )}
          {job.ai_work_arrangement && (
            <MetadataPill icon={<Wifi className="w-3.5 h-3.5" />} label={job.ai_work_arrangement} />
          )}
          {job.ai_employment_type && (
            <MetadataPill icon={<Clock className="w-3.5 h-3.5" />} label={job.ai_employment_type} />
          )}
          {job.salary && (
            <MetadataPill icon={<DollarSign className="w-3.5 h-3.5" />} label={job.salary} />
          )}
        </div>
      )}

      {/* Match Reasoning */}
      {job.match_reasoning && (
        <Section title="Match Reasoning" icon={<Briefcase className="w-4 h-4 text-cyan-600" />}>
          <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-4 text-sm text-slate-700 leading-relaxed">
            {job.match_reasoning}
          </div>
        </Section>
      )}

      {/* Key Alignments */}
      {job.key_alignments.length > 0 && (
        <Section title="Key Alignments" icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}>
          <div className="space-y-2">
            {job.key_alignments.map((alignment, i) => (
              <InteractivePoint
                key={i}
                text={typeof alignment === 'string' ? alignment : String(alignment)}
                type="alignment"
                jobId={jobId}
                originalScore={job.claude_score || 0}
                onFeedback={(data) => feedbackMutation.mutate(data)}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Potential Gaps */}
      {job.potential_gaps.length > 0 && (
        <Section title="Potential Gaps" icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}>
          <div className="space-y-2">
            {job.potential_gaps.map((gap, i) => (
              <InteractivePoint
                key={i}
                text={typeof gap === 'string' ? gap : String(gap)}
                type="gap"
                jobId={jobId}
                originalScore={job.claude_score || 0}
                onFeedback={(data) => feedbackMutation.mutate(data)}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Required Competencies */}
      {job.ai_competencies.length > 0 && (
        <Section title="Required Competencies" icon={<GraduationCap className="w-4 h-4 text-indigo-600" />}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {job.ai_competencies.map((comp) => {
              const matched = job.competency_match_map[comp];
              const claimed = !matched && (claimedCompSet.has(comp.toLowerCase()) || newlyClaimed.has(`competency:${comp}`));
              const isClaiming = claimingItem === `competency:${comp}`;
              const canClaim = !matched && !claimed;

              return (
                <div
                  key={comp}
                  onClick={canClaim ? () => handleClaim(comp, 'competency') : undefined}
                  className={`flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border-l-[3px] transition-all ${
                    matched
                      ? 'bg-emerald-50 border-l-emerald-500 border border-emerald-100'
                      : claimed
                      ? 'bg-blue-50 border-l-blue-500 border border-blue-100'
                      : 'bg-slate-50 border-l-slate-300 border border-slate-200 cursor-pointer hover:bg-slate-100 hover:border-l-slate-400'
                  }`}
                >
                  <span className={`text-sm font-medium ${
                    matched ? 'text-emerald-800' : claimed ? 'text-blue-800' : 'text-slate-600'
                  }`}>
                    {comp}
                  </span>
                  {isClaiming ? (
                    <Loader2 className="w-3.5 h-3.5 text-slate-400 animate-spin flex-shrink-0" />
                  ) : matched ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-100 rounded-full px-2 py-0.5">
                      <Check className="w-3 h-3" /> Matched
                    </span>
                  ) : claimed ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 bg-blue-100 rounded-full px-2 py-0.5">
                      <Check className="w-3 h-3" /> Claimed
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">Click to claim</span>
                  )}
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-slate-400 italic">
            Green = matched to your profile. Blue = claimed. Click gray items to claim them.
          </p>
        </Section>
      )}

      {/* Technical Skills Required */}
      {job.ai_key_skills.length > 0 && (
        <Section title="Technical Skills Required" icon={<Briefcase className="w-4 h-4 text-emerald-600" />}>
          <div className="flex flex-wrap gap-2">
            {job.ai_key_skills.map((skill) => {
              const matched = job.skill_match_map[skill];
              const claimed = !matched && (claimedSkillSet.has(skill.toLowerCase()) || newlyClaimed.has(`skill:${skill}`));
              const isClaiming = claimingItem === `skill:${skill}`;
              const canClaim = !matched && !claimed;

              return (
                <span
                  key={skill}
                  onClick={canClaim ? () => handleClaim(skill, 'skill') : undefined}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                    matched
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                      : claimed
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'bg-slate-50 text-slate-500 border-slate-200 cursor-pointer hover:bg-slate-100 hover:border-slate-300'
                  }`}
                >
                  {isClaiming ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (matched || claimed) ? (
                    <Check className="w-3 h-3" />
                  ) : null}
                  {skill}
                </span>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-slate-400 italic">
            Green = matched. Blue = claimed. Click gray items to claim them.
          </p>
        </Section>
      )}

      {/* Requirements Summary */}
      {job.ai_requirements_summary && (
        <Section title="Requirements Summary" icon={<Briefcase className="w-4 h-4 text-cyan-600" />}>
          <p className="text-sm text-slate-700 leading-relaxed">{job.ai_requirements_summary}</p>
        </Section>
      )}

      {/* Core Responsibilities */}
      {job.ai_core_responsibilities && (
        <Section title="Core Responsibilities" icon={<Briefcase className="w-4 h-4 text-cyan-600" />}>
          <p className="text-sm text-slate-700 leading-relaxed">{job.ai_core_responsibilities}</p>
        </Section>
      )}

      {/* Description */}
      {job.description && (
        <Section title="Full Description" icon={<Briefcase className="w-4 h-4 text-slate-400" />}>
          <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto border border-slate-100 rounded-xl p-4 bg-slate-50">
            {job.description}
          </div>
        </Section>
      )}

      {showResumeModal && (
        <ResumeModal
          jobId={jobId}
          jobTitle={job.title}
          company={job.company}
          onClose={() => setShowResumeModal(false)}
        />
      )}

      {showCoverLetterModal && (
        <CoverLetterModal
          jobId={jobId}
          jobTitle={job.title}
          company={job.company}
          onClose={() => setShowCoverLetterModal(false)}
        />
      )}
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-900 mb-3">
        {icon}
        {title}
      </h4>
      {children}
    </div>
  );
}

function MetadataPill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-xs font-medium">
      {icon}
      {label}
    </span>
  );
}

function InteractivePoint({ 
  text, 
  type, 
  originalScore,
  onFeedback 
}: { 
  text: string; 
  type: 'alignment' | 'gap';
  jobId: number;
  originalScore: number;
  onFeedback: (data: any) => void;
}) {
  const [rated, setRated] = useState<'agree' | 'disagree' | null>(null);

  const handleRate = (feedbackType: 'agree' | 'disagree') => {
    setRated(feedbackType);
    onFeedback({
      feedback_type: feedbackType,
      match_score_original: originalScore,
      feedback_reason: `${type === 'alignment' ? 'Alignment' : 'Gap'} point: "${text}" - User marked as ${feedbackType}`
    });
  };

  return (
    <div className={`group flex items-start justify-between gap-3 p-3 rounded-xl border transition-all ${
      type === 'alignment' 
        ? 'bg-emerald-50/50 border-emerald-100 hover:border-emerald-200' 
        : 'bg-amber-50/50 border-amber-100 hover:border-amber-200'
    }`}>
      <div className="flex items-start gap-2.5 min-w-0">
        {type === 'alignment' ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        )}
        <span className="text-sm text-slate-700 leading-relaxed">{text}</span>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {rated ? (
          <span className={`text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider ${
            rated === 'agree' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
          }`}>
            {rated === 'agree' ? 'Correct' : 'Incorrect'}
          </span>
        ) : (
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => handleRate('agree')}
              className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-100/50 rounded-lg transition-colors"
              title="This is correct"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleRate('disagree')}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-100/50 rounded-lg transition-colors"
              title="This is incorrect"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
