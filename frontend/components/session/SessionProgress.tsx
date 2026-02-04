type SessionProgressProps = {
  answeredCount: number;
  maxQuestions?: number | null;
};

export default function SessionProgress({
  answeredCount,
  maxQuestions,
}: SessionProgressProps) {
  return (
    <div className="rounded border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
      Questions answered: {answeredCount}
      {typeof maxQuestions === "number" ? ` / ${maxQuestions}` : ""}
    </div>
  );
}
