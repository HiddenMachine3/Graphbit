type ConsumeProgressBarProps = {
  consumed: number;
  total: number;
};

export default function ConsumeProgressBar({ consumed, total }: ConsumeProgressBarProps) {
  const clampedTotal = total > 0 ? total : 1;
  const progress = Math.min(consumed, clampedTotal);
  const percent = Math.round((progress / clampedTotal) * 100);

  return (
    <div className="rounded border border-border-default bg-bg-surface p-3">
      <div className="flex items-center justify-between text-xs font-body text-text-muted">
        <span>Consumed</span>
        <span>{progress} / {clampedTotal}</span>
      </div>
      <div className="mt-2 h-2 w-full rounded bg-bg-elevated">
        <div
          className="h-2 rounded bg-accent"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
