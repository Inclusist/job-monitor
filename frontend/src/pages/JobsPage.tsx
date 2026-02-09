import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Clock,
  Play,
  EyeOff,
  ExternalLink,
  MapPin,
  Building2,
  Calendar,
  Briefcase,
  AlertCircle,
  Search,
  X,
  Loader2,
} from 'lucide-react';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import FilterBar from '../components/ui/FilterBar';
import Badge from '../components/ui/Badge';
import ScoreDisplay from '../components/ui/ScoreDisplay';
import MatchingProgress from '../components/ui/MatchingProgress';
import SlideOver from '../components/ui/SlideOver';
import JobDetailPanel from '../components/JobDetailPanel';
import { useJobs, useHideJob, useRunMatching } from '../hooks/useJobs';
import { useMatchingStatus } from '../hooks/useMatchingStatus';
import { useAuth } from '../contexts/AuthContext';
import { searchJobs } from '../services/jobs';
import type { Job, SearchResult } from '../types';

export default function JobsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState({ priority: '', status: '', min_score: 0 });
  const { data, isLoading, error } = useJobs(filters);
  const hideJob = useHideJob();
  const runMatching = useRunMatching();
  const { data: matchingStatus } = useMatchingStatus(true);
  const [matchingError, setMatchingError] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchStats, setSearchStats] = useState<Record<string, unknown> | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const handleRunMatching = () => {
    setMatchingError('');
    runMatching.mutate(undefined, {
      onError: (err) => {
        const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to start matching';
        setMatchingError(msg);
      },
    });
  };

  const handleSearch = async () => {
    const query = searchQuery.trim();
    if (!query) return;

    setIsSearching(true);
    setSearchError('');
    try {
      const data = await searchJobs(query);
      setSearchResults(data.results);
      setSearchStats(data.stats);
    } catch (err) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Search failed';
      setSearchError(msg);
      setSearchResults(null);
      setSearchStats(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
    setSearchStats(null);
    setSearchError('');
  };

  const isSearchActive = searchResults !== null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50/30">
      <Header />
      {matchingStatus && <MatchingProgress status={matchingStatus} />}

      <main className="pt-28 pb-16 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Page header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm mb-8"
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                  <Briefcase className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
                  Matched Jobs
                </h1>
                <p className="text-slate-500 text-sm mt-1">
                  {data ? `${data.total} matches found` : 'Loading...'}
                  {user && <span className="ml-2 text-slate-400">for {user.name}</span>}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <a
                  href="/deleted-jobs"
                  className="text-sm text-slate-500 hover:text-slate-700 transition-colors"
                >
                  Hidden Jobs
                </a>
                <button
                  onClick={handleRunMatching}
                  disabled={runMatching.isPending || matchingStatus?.status === 'running'}
                  className="px-5 py-2.5 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  Run Matching
                </button>
              </div>
            </div>

            {matchingError && (
              <div className="mt-4 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {matchingError}
              </div>
            )}

            {data && !data.has_cv && (
              <div className="mt-4 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                Upload your CV first to enable job matching.
              </div>
            )}
          </motion.div>

          {/* Search bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="mb-8"
          >
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search all jobs (e.g. data engineer, product manager)..."
                  className="w-full pl-10 pr-4 py-2.5 border border-cyan-200 rounded-xl bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={isSearching || !searchQuery.trim()}
                className="px-5 py-2.5 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Search
              </button>
              {isSearchActive && (
                <button
                  onClick={handleClearSearch}
                  className="px-4 py-2.5 border border-slate-200 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-50 transition-colors flex items-center gap-1.5"
                >
                  <X className="w-4 h-4" />
                  Clear
                </button>
              )}
            </div>
            {searchError && (
              <div className="mt-3 flex items-center gap-2 text-sm text-rose-600">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {searchError}
              </div>
            )}
          </motion.div>

          {/* Search results mode */}
          {isSearchActive && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex items-center gap-2 mb-4">
                <Search className="w-5 h-5 text-cyan-600" strokeWidth={1.5} />
                <h2 className="text-lg font-semibold text-slate-900">Search Results</h2>
                <span className="text-sm text-slate-400">
                  ({searchResults.length} found
                  {searchStats && typeof searchStats.total_jobs === 'number' && ` from ${searchStats.total_jobs} jobs`})
                </span>
              </div>

              {searchResults.length === 0 ? (
                <div className="text-center py-16">
                  <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" strokeWidth={1.5} />
                  <h3 className="text-lg font-semibold text-slate-700 mb-2">No results found</h3>
                  <p className="text-slate-500 text-sm">Try a different search term or broaden your query.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((result) => (
                    <SearchResultRow key={result.job_id} result={result} onClick={() => setSelectedJobId(result.job_id)} />
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Normal matched jobs mode (hidden during search) */}
          {!isSearchActive && (
            <>
              {/* Filters */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="mb-8"
              >
                <FilterBar onApply={setFilters} initialFilters={filters} />
              </motion.div>

              {/* Loading state */}
              {isLoading && <LoadingSkeleton />}

              {/* Error state */}
              {error && (
                <div className="text-center py-16">
                  <p className="text-slate-500">Failed to load jobs. Please try again.</p>
                </div>
              )}

              {/* Jobs content */}
              {data && !isLoading && (
                <>
                  {data.total === 0 ? (
                    <EmptyState hasCv={data.has_cv} />
                  ) : (
                    <div className="space-y-8">
                      {/* New Matches */}
                      {data.new_jobs.length > 0 && (
                        <JobSection
                          title="New Matches"
                          icon={<Sparkles className="w-5 h-5 text-emerald-600" strokeWidth={1.5} />}
                          jobs={data.new_jobs}
                          borderColor="border-l-emerald-500"
                          onHide={(id) => hideJob.mutate(id)}
                          hidingId={hideJob.isPending ? (hideJob.variables as number) : undefined}
                          onJobClick={setSelectedJobId}
                        />
                      )}

                      {/* Previous Jobs */}
                      {data.previous_jobs.length > 0 && (
                        <JobSection
                          title="Previous Jobs"
                          icon={<Clock className="w-5 h-5 text-slate-500" strokeWidth={1.5} />}
                          jobs={data.previous_jobs}
                          borderColor="border-l-slate-300"
                          onHide={(id) => hideJob.mutate(id)}
                          hidingId={hideJob.isPending ? (hideJob.variables as number) : undefined}
                          onJobClick={setSelectedJobId}
                        />
                      )}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </main>

      <Footer />

      <SlideOver
        open={selectedJobId !== null}
        onClose={() => setSelectedJobId(null)}
        title="Job Details"
      >
        {selectedJobId !== null && <JobDetailPanel jobId={selectedJobId} />}
      </SlideOver>
    </div>
  );
}

function SearchResultRow({ result, onClick }: { result: SearchResult; onClick: () => void }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onClick={onClick}
      className="border border-cyan-200 rounded-xl bg-white shadow-sm hover:shadow-md transition-shadow border-l-4 border-l-cyan-500 p-5 cursor-pointer"
    >
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-slate-900 truncate">{result.title}</h3>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-sm text-slate-500">
            {result.company && (
              <span className="flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5" />
                {result.company}
              </span>
            )}
            {result.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                {result.location}
              </span>
            )}
            {result.discovered_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(result.discovered_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <ScoreDisplay score={result.match_score} label="Similarity" />
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {result.url && (
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-2 text-slate-400 hover:text-cyan-600 transition-colors rounded-lg hover:bg-cyan-50"
              title="View job posting"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function JobSection({
  title,
  icon,
  jobs,
  borderColor,
  onHide,
  hidingId,
  onJobClick,
}: {
  title: string;
  icon: React.ReactNode;
  jobs: Job[];
  borderColor: string;
  onHide: (id: number) => void;
  hidingId?: number;
  onJobClick: (id: number) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <span className="text-sm text-slate-400">({jobs.length})</span>
      </div>
      <div className="space-y-3">
        {jobs.map((job) => (
          <JobRow
            key={job.job_id || job.id || job.job_table_id}
            job={job}
            borderColor={borderColor}
            onHide={onHide}
            isHiding={hidingId === (job.job_table_id || job.id)}
            onClick={() => onJobClick(job.job_table_id || job.id || 0)}
          />
        ))}
      </div>
    </motion.div>
  );
}

function JobRow({
  job,
  borderColor,
  onHide,
  isHiding,
  onClick,
}: {
  job: Job;
  borderColor: string;
  onHide: (id: number) => void;
  isHiding: boolean;
  onClick: () => void;
}) {
  const jobId = job.job_table_id || job.id || 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: isHiding ? 0.5 : 1 }}
      onClick={onClick}
      className={`border border-cyan-200 rounded-xl bg-white shadow-sm hover:shadow-md transition-shadow border-l-4 ${borderColor} p-5 cursor-pointer`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        {/* Job info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-slate-900 truncate">{job.title}</h3>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-sm text-slate-500">
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
            {job.created_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(job.created_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>

        {/* Scores */}
        <div className="flex items-center gap-4">
          <ScoreDisplay score={job.match_score} label="Match" />
          {job.semantic_score != null && job.claude_score != null && (
            <ScoreDisplay score={job.semantic_score} label="Semantic" />
          )}
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2">
          {job.priority && <Badge type="priority" value={job.priority} />}
          {job.status && job.status !== 'new' && <Badge type="status" value={job.status} />}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-2 text-slate-400 hover:text-cyan-600 transition-colors rounded-lg hover:bg-cyan-50"
              title="View job posting"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onHide(jobId); }}
            disabled={isHiding}
            className="p-2 text-slate-400 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-50 disabled:opacity-50"
            title="Hide job"
          >
            <EyeOff className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function EmptyState({ hasCv }: { hasCv: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-center py-20"
    >
      <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" strokeWidth={1.5} />
      <h3 className="text-lg font-semibold text-slate-700 mb-2">No matched jobs yet</h3>
      <p className="text-slate-500 text-sm max-w-md mx-auto">
        {hasCv
          ? 'Click "Run Matching" to analyze jobs against your CV and find the best matches.'
          : 'Upload your CV first, then run matching to find jobs that fit your skills.'}
      </p>
    </motion.div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="border border-cyan-100 rounded-xl p-5 bg-white animate-pulse">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="h-4 bg-slate-200 rounded w-2/3 mb-2" />
              <div className="h-3 bg-slate-100 rounded w-1/3" />
            </div>
            <div className="h-8 w-12 bg-slate-100 rounded" />
            <div className="h-6 w-16 bg-slate-100 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}
