import { useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';

interface FilterBarProps {
  onApply: (filters: { priority: string; status: string; min_score: number }) => void;
  initialFilters?: { priority: string; status: string; min_score: number };
}

export default function FilterBar({ onApply, initialFilters }: FilterBarProps) {
  const [priority, setPriority] = useState(initialFilters?.priority || '');
  const [status, setStatus] = useState(initialFilters?.status || '');
  const [minScore, setMinScore] = useState(initialFilters?.min_score || 0);

  const handleApply = () => {
    onApply({ priority, status, min_score: minScore });
  };

  const handleClear = () => {
    setPriority('');
    setStatus('');
    setMinScore(0);
    onApply({ priority: '', status: '', min_score: 0 });
  };

  return (
    <div className="border border-cyan-200 rounded-2xl p-5 bg-white shadow-sm">
      <div className="flex items-center space-x-2 mb-4">
        <SlidersHorizontal className="w-4 h-4 text-cyan-600" strokeWidth={1.5} />
        <h3 className="text-sm font-semibold text-slate-900">Filters</h3>
      </div>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Priority</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          >
            <option value="">All</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          >
            <option value="">All</option>
            <option value="not_viewed">Not Viewed</option>
            <option value="viewed">Viewed</option>
            <option value="shortlisted">Shortlisted</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Min Score</label>
          <input
            type="number"
            value={minScore || ''}
            onChange={(e) => setMinScore(Number(e.target.value) || 0)}
            min={0}
            max={100}
            placeholder="0"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
        </div>
      </div>
      <div className="flex flex-col gap-2 mt-5">
        <button
          onClick={handleApply}
          className="w-full px-4 py-2 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors"
        >
          Apply
        </button>
        <button
          onClick={handleClear}
          className="w-full px-4 py-2 text-slate-600 text-sm font-medium hover:text-slate-900 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
