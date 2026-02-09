interface BadgeProps {
  type: 'priority' | 'status';
  value: string;
}

const priorityColors: Record<string, string> = {
  high: 'bg-emerald-100 text-emerald-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-rose-100 text-rose-800',
};

const statusColors: Record<string, string> = {
  new: 'bg-slate-100 text-slate-700',
  reviewed: 'bg-cyan-100 text-cyan-800',
  shortlisted: 'bg-amber-100 text-amber-800',
  applying: 'bg-emerald-100 text-emerald-800',
};

export default function Badge({ type, value }: BadgeProps) {
  const colors =
    type === 'priority'
      ? priorityColors[value] || 'bg-slate-100 text-slate-700'
      : statusColors[value] || 'bg-slate-100 text-slate-700';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${colors}`}>
      {value}
    </span>
  );
}
