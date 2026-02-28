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
    <div className="rounded-2xl border border-border-default bg-bg-elevated p-6">
      <div
        className={`text-sm font-semibold font-body ${
          feedback.correct ? "text-emerald-600" : "text-rose-600"
        }`}
      >
        {feedback.correct ? "Correct" : "Incorrect"}
      </div>
      {feedback.correct_answer && !feedback.correct && (
        <div className="mt-2 text-sm font-body text-text-secondary">
          <div>Correct answer:</div>
          <RichContent content={feedback.correct_answer} className="mt-1" />
        </div>
      )}
      {!feedback.correct && feedback.explanation && (
        <div className="mt-2 text-sm font-body text-text-secondary">
          <RichContent content={feedback.explanation} />
        </div>
      )}
      <button
        className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
        onClick={onNext}
        disabled={disabled}
      >
        Next Question
      </button>
    </div>
  );
}
