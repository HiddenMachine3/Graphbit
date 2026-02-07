import type { RevisionFeedbackDTO } from "../../lib/types";

type FeedbackPanelProps = {
  feedback: RevisionFeedbackDTO;
  onNext: () => void;
  disabled?: boolean;
};

export default function FeedbackPanel({
  feedback,
  onNext,
  disabled = false,
}: FeedbackPanelProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-6">
      <div
        className={`text-sm font-semibold ${
          feedback.correct ? "text-emerald-600" : "text-rose-600"
        }`}
      >
        {feedback.correct ? "Correct" : "Incorrect"}
      </div>
      {feedback.correct_answer && !feedback.correct && (
        <div className="mt-2 text-sm text-slate-600">
          Correct answer: {feedback.correct_answer}
        </div>
      )}
      {!feedback.correct && feedback.explanation && (
        <div className="mt-2 text-sm text-slate-600">
          {feedback.explanation}
        </div>
      )}
      <button
        className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
        onClick={onNext}
        disabled={disabled}
      >
        Next Question
      </button>
    </div>
  );
}
