import type { RevisionFeedbackDTO } from "../../lib/types";
import RichContent from "./RichContent";

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
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
      <div
        className={`text-sm font-semibold ${
          feedback.correct ? "text-emerald-600" : "text-rose-600"
        }`}
      >
        {feedback.correct ? "Correct" : "Incorrect"}
      </div>
      {feedback.correct_answer && !feedback.correct && (
        <div className="mt-2 text-sm text-slate-300">
          <div>Correct answer:</div>
          <RichContent content={feedback.correct_answer} className="mt-1" />
        </div>
      )}
      {!feedback.correct && feedback.explanation && (
        <div className="mt-2 text-sm text-slate-300">
          <RichContent content={feedback.explanation} />
        </div>
      )}
      <button
        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-60"
        onClick={onNext}
        disabled={disabled}
      >
        Next Question
      </button>
    </div>
  );
}
