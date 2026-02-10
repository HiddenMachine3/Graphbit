type SessionProgressProps = {
  answeredCount: number;
  maxQuestions?: number | null;
};

export default function SessionProgress({
  answeredCount,
  maxQuestions,
}: SessionProgressProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm text-slate-300">
      Questions answered: {answeredCount}
      {typeof maxQuestions === "number" ? ` / ${maxQuestions}` : ""}
    </div>
  );
}
