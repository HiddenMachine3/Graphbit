type SessionProgressProps = {
  answeredCount: number;
  maxQuestions?: number | null;
};

export default function SessionProgress({
  answeredCount,
  maxQuestions,
}: SessionProgressProps) {
  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface px-4 py-3 text-sm font-body text-text-secondary">
      Questions answered: {answeredCount}
      {typeof maxQuestions === "number" ? ` / ${maxQuestions}` : ""}
    </div>
  );
}
