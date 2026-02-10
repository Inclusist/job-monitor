import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard,
  ExternalLink,
  MapPin,
  Building2,
  Calendar,
  Trash2,
  Loader2,
  AlertCircle,
  Briefcase,
  FileText,
  Eye,
  Pencil,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import Badge from '../components/ui/Badge';
import SlideOver from '../components/ui/SlideOver';
import JobDetailPanel from '../components/JobDetailPanel';
import DocumentViewerModal from '../components/ui/DocumentViewerModal';
import { getDashboard, updateJobStatus, removeShortlist } from '../services/jobs';
import type { DashboardJob, DashboardStatus } from '../types';

const STATUS_OPTIONS: { value: DashboardStatus; label: string }[] = [
  { value: 'shortlisted', label: 'Planning to Apply' },
  { value: 'applying', label: 'Applying' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'offered', label: 'Offered' },
  { value: 'rejected', label: 'Rejected' },
];

function getScoreColor(score: number): string {
  if (score >= 85) return 'text-emerald-600';
  if (score >= 70) return 'text-cyan-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-slate-500';
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  });
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [modalState, setModalState] = useState<{
    docType: 'resume' | 'cover_letter';
    docId: number;
    mode: 'view' | 'edit';
  } | null>(null);

  const statusMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: number; status: DashboardStatus }) =>
      updateJobStatus(jobId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (jobId: number) => removeShortlist(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const jobs = data?.jobs ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-cyan-50 via-white to-white">
      <Header />
      <main className="max-w-5xl mx-auto px-6 pt-28 pb-20">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm mb-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <LayoutDashboard className="w-6 h-6 text-cyan-600" />
              <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
              {data && (
                <span className="text-sm text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
                  {data.count} {data.count === 1 ? 'job' : 'jobs'}
                </span>
              )}
            </div>
            <Link
              to="/jobs"
              className="px-4 py-2 text-sm font-medium text-cyan-600 border border-cyan-200 rounded-xl hover:bg-cyan-50 transition-colors"
            >
              Browse Jobs
            </Link>
          </div>
        </motion.div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            Failed to load dashboard.
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && jobs.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-700 mb-2">No jobs on your dashboard yet</h2>
            <p className="text-slate-500 mb-6">
              Browse jobs and click "Add to Dashboard" to start tracking your applications.
            </p>
            <Link
              to="/jobs"
              className="px-6 py-3 bg-cyan-600 text-white font-semibold rounded-xl hover:bg-cyan-500 transition-colors"
            >
              Browse Jobs
            </Link>
          </motion.div>
        )}

        {/* Job cards */}
        <div className="space-y-4">
          {jobs.map((job, i) => (
            <motion.div
              key={job.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="border border-cyan-200 rounded-2xl p-6 bg-white shadow-sm hover:shadow-md transition-shadow"
            >
              <DashboardJobCard
                job={job}
                onStatusChange={(status) => statusMutation.mutate({ jobId: job.id, status })}
                onRemove={() => removeMutation.mutate(job.id)}
                onViewDetail={() => setSelectedJobId(job.id)}
                onOpenDocument={(docType, docId, mode) => setModalState({ docType, docId, mode })}
                isUpdating={statusMutation.isPending || removeMutation.isPending}
              />
            </motion.div>
          ))}
        </div>
      </main>
      <Footer />

      {/* Job detail slide-over */}
      <SlideOver
        isOpen={selectedJobId !== null}
        onClose={() => setSelectedJobId(null)}
        title="Job Details"
      >
        {selectedJobId && <JobDetailPanel jobId={selectedJobId} />}
      </SlideOver>

      {modalState && (
        <DocumentViewerModal
          docType={modalState.docType}
          docId={modalState.docId}
          initialMode={modalState.mode}
          onClose={() => setModalState(null)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['dashboard'] })}
        />
      )}
    </div>
  );
}

function DashboardJobCard({
  job,
  onStatusChange,
  onRemove,
  onViewDetail,
  onOpenDocument,
  isUpdating,
}: {
  job: DashboardJob;
  onStatusChange: (status: DashboardStatus) => void;
  onRemove: () => void;
  onViewDetail: () => void;
  onOpenDocument: (docType: 'resume' | 'cover_letter', docId: number, mode: 'view' | 'edit') => void;
  isUpdating: boolean;
}) {
  const MAX_ALIGNMENTS = 3;
  const alignments = job.key_alignments ?? [];
  const shown = alignments.slice(0, MAX_ALIGNMENTS);
  const remaining = alignments.length - MAX_ALIGNMENTS;

  return (
    <div className="space-y-4">
      {/* Top row: title + score */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <button
            onClick={onViewDetail}
            className="text-lg font-bold text-slate-900 hover:text-cyan-600 transition-colors text-left"
          >
            {job.title}
          </button>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-sm text-slate-500">
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
          </div>
          {job.priority && (
            <div className="mt-2">
              <Badge type="priority" value={job.priority} />
            </div>
          )}
        </div>
        {job.match_score != null && (
          <div className="flex flex-col items-center flex-shrink-0">
            <span className={`text-2xl font-bold tabular-nums ${getScoreColor(Math.round(job.match_score))}`}>
              {Math.round(job.match_score)}
            </span>
            <span className="text-xs text-slate-400">Match</span>
          </div>
        )}
      </div>

      {/* Match reasoning */}
      {job.match_reasoning && (
        <p className="text-sm text-slate-600 leading-relaxed line-clamp-3">
          {job.match_reasoning}
        </p>
      )}

      {/* Key alignments */}
      {shown.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {shown.map((alignment, i) => (
            <span
              key={i}
              className="inline-flex items-center px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-medium"
            >
              {typeof alignment === 'string' ? (alignment.length > 60 ? alignment.slice(0, 60) + '...' : alignment) : String(alignment)}
            </span>
          ))}
          {remaining > 0 && (
            <span className="inline-flex items-center px-2.5 py-1 bg-slate-100 text-slate-500 rounded-lg text-xs font-medium">
              +{remaining} more
            </span>
          )}
        </div>
      )}

      {/* Documents row */}
      {(job.resume_id || job.cover_letter_id) && (
        <div className="flex flex-wrap items-center gap-3">
          {job.resume_id && (
            <div className="inline-flex items-center gap-1.5 bg-slate-50 rounded-lg px-3 py-1.5">
              <FileText className="w-3.5 h-3.5 text-cyan-600" />
              <span className="text-xs font-medium text-slate-600">Resume</span>
              <button
                onClick={() => onOpenDocument('resume', job.resume_id!, 'view')}
                className="p-0.5 text-slate-400 hover:text-cyan-600 transition-colors rounded"
                title="View resume"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onOpenDocument('resume', job.resume_id!, 'edit')}
                className="p-0.5 text-slate-400 hover:text-cyan-600 transition-colors rounded"
                title="Edit resume"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          {job.cover_letter_id && (
            <div className="inline-flex items-center gap-1.5 bg-slate-50 rounded-lg px-3 py-1.5">
              <FileText className="w-3.5 h-3.5 text-indigo-600" />
              <span className="text-xs font-medium text-slate-600">Cover Letter</span>
              <button
                onClick={() => onOpenDocument('cover_letter', job.cover_letter_id!, 'view')}
                className="p-0.5 text-slate-400 hover:text-cyan-600 transition-colors rounded"
                title="View cover letter"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onOpenDocument('cover_letter', job.cover_letter_id!, 'edit')}
                className="p-0.5 text-slate-400 hover:text-cyan-600 transition-colors rounded"
                title="Edit cover letter"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Bottom row: status dropdown + actions */}
      <div className="flex items-center justify-between gap-4 pt-2 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 font-medium">Status:</label>
          <select
            value={job.status}
            onChange={(e) => onStatusChange(e.target.value as DashboardStatus)}
            disabled={isUpdating}
            className="text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 disabled:opacity-50"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-cyan-600 border border-slate-200 rounded-lg hover:bg-cyan-50 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              View Posting
            </a>
          )}
          <button
            onClick={onRemove}
            disabled={isUpdating}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-rose-600 border border-slate-200 rounded-lg hover:bg-rose-50 hover:border-rose-200 transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}
