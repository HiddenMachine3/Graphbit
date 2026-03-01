"use client";

import { useMemo, useState } from "react";

export type SharedQAPair = {
  question: string;
  answer: string;
};

type SharedQuestionAnswerPanelProps = {
  pairs: SharedQAPair[];
  title?: string;
  subtitle?: string;
  showPerformanceRating?: boolean;
  disabled?: boolean;
  onRatePerformance?: (performance: "bad" | "ok" | "good" | "great") => void;
  onComplete?: () => void;
};

export default function SharedQuestionAnswerPanel({
  pairs,
  title = "Question",
  subtitle,
  showPerformanceRating = false,
  disabled = false,
  onRatePerformance,
  onComplete,
}: SharedQuestionAnswerPanelProps) {
  const normalizedPairs = useMemo(
    () =>
      (pairs ?? [])
        .map((pair) => ({
          question: String(pair?.question ?? "").trim(),
          answer: String(pair?.answer ?? "").trim(),
        }))
        .filter((pair) => pair.question),
    [pairs]
  );

  const [index, setIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);

  const current = normalizedPairs[index];
  const isLast = index >= normalizedPairs.length - 1;

  if (!current) {
    return (
      <div className="rounded-2xl border border-border-default bg-bg-surface p-6 text-sm font-body text-text-secondary">
        No questions available.
      </div>
    );
  }

  const handleNext = () => {
    if (isLast) {
      onComplete?.();
      return;
    }
    setIndex((prev) => prev + 1);
    setShowAnswer(false);
  };

  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface p-6 backdrop-blur">
      <div className="label-caps text-text-muted">{title}</div>
      {subtitle ? <div className="mt-1 text-sm font-body text-text-secondary">{subtitle}</div> : null}
      <div className="mt-3 text-lg font-semibold font-heading text-text-primary">{current.question}</div>

      {!showAnswer ? (
        <button
          className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
          onClick={() => setShowAnswer(true)}
          disabled={disabled}
        >
          Show answer
        </button>
      ) : (
        <div className="mt-4 rounded-lg border border-border-default bg-bg-elevated p-4">
          <div className="label-caps text-text-muted">Answer</div>
          <div className="mt-2 text-sm font-body text-text-primary whitespace-pre-wrap">{current.answer}</div>
        </div>
      )}

      {showAnswer && showPerformanceRating && onRatePerformance ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="rounded-lg border border-rose-500/60 px-3 py-2 text-sm font-body text-rose-100 transition hover:border-rose-400 disabled:opacity-60"
            onClick={() => onRatePerformance("bad")}
            disabled={disabled}
          >
            Bad
          </button>
          <button
            className="rounded-lg border border-amber-500/60 px-3 py-2 text-sm font-body text-amber-100 transition hover:border-amber-400 disabled:opacity-60"
            onClick={() => onRatePerformance("ok")}
            disabled={disabled}
          >
            Ok
          </button>
          <button
            className="rounded-lg border border-emerald-500/60 px-3 py-2 text-sm font-body text-emerald-100 transition hover:border-emerald-400 disabled:opacity-60"
            onClick={() => onRatePerformance("good")}
            disabled={disabled}
          >
            Good
          </button>
          <button
            className="rounded-lg border border-blue-500/60 px-3 py-2 text-sm font-body text-blue-100 transition hover:border-blue-400 disabled:opacity-60"
            onClick={() => onRatePerformance("great")}
            disabled={disabled}
          >
            Great
          </button>
        </div>
      ) : null}

      {showAnswer && !showPerformanceRating ? (
        <div className="mt-4">
          <button
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
            onClick={handleNext}
            disabled={disabled}
          >
            {isLast ? "Finish" : "Next"}
          </button>
        </div>
      ) : null}

      <div className="mt-4 text-xs font-body text-text-muted">
        {index + 1} / {normalizedPairs.length}
      </div>
    </div>
  );
}
