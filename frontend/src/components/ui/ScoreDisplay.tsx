interface ScoreDisplayProps {
  score: number | null | undefined;
  label?: string;
}

function getScoreColor(score: number): string {
  if (score >= 85) return 'text-emerald-600';
  if (score >= 70) return 'text-cyan-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-slate-500';
}

export default function ScoreDisplay({ score, label }: ScoreDisplayProps) {
  if (score == null) return null;

  const rounded = Math.round(score);

  return (
    <div className="flex flex-col items-center">
      <span className={`text-lg font-bold tabular-nums ${getScoreColor(rounded)}`}>
        {rounded}
      </span>
      {label && <span className="text-xs text-slate-400">{label}</span>}
    </div>
  );
}
