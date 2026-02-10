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
} from 'lucide-react';
import Badge from './ui/Badge';
import ScoreDisplay from './ui/ScoreDisplay';
import ResumeModal from './ResumeModal';
import CoverLetterModal from './CoverLetterModal';
import { useJobDetail } from '../hooks/useJobDetail';
import { claimItems, shortlistJob, removeShortlist, analyzeJob } from '../services/jobs';
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

      {/* Scores */}
      {(job.claude_score != null || job.semantic_score != null) && (
        <div className="flex items-center gap-6 p-4 bg-slate-50 rounded-xl">
          {job.claude_score != null && <ScoreDisplay score={job.claude_score} label="AI Match" />}
          {job.semantic_score != null && <ScoreDisplay score={job.semantic_score} label="Semantic" />}
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
          <ul className="space-y-2">
            {job.key_alignments.map((alignment, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>{typeof alignment === 'string' ? alignment : String(alignment)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Potential Gaps */}
      {job.potential_gaps.length > 0 && (
        <Section title="Potential Gaps" icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}>
          <ul className="space-y-2">
            {job.potential_gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <span>{typeof gap === 'string' ? gap : String(gap)}</span>
              </li>
            ))}
          </ul>
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
