import type { QuestionDTO, RevisionFeedbackDTO } from "../../lib/types";
import RichContent from "./RichContent";

type QuestionCardProps = {
  question: QuestionDTO;
  selectedOption?: string;
  onOptionSelect?: (option: string) => void;
  disabled?: boolean;
  feedback?: RevisionFeedbackDTO | null;
};

export default function QuestionCard({
  question,
  selectedOption,
  onOptionSelect,
  disabled = false,
  feedback = null,
}: QuestionCardProps) {
  const isMCQ = question.question_type === "MCQ";

  return (
    <div className="rounded-2xl border border-border-default bg-bg-elevated p-6">
      <div className="label-caps text-text-muted">
        {question.question_type}
      </div>
      <div className="mt-2 text-lg font-semibold font-heading text-text-primary">
        <RichContent content={question.text} className="text-lg font-semibold font-heading text-text-primary" />
      </div>

      {isMCQ && question.options && (
        <div className="mt-4 space-y-2">
          {question.options.map((option, index) => (
            <button
              key={index}
              onClick={() => onOptionSelect?.(option)}
              disabled={disabled}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm font-medium font-body transition-colors ${
                selectedOption === option
                  ? "border-accent/60 bg-accent/15 text-text-primary ring-2 ring-accent/40"
                  : "border-border-default bg-bg-elevated text-text-primary hover:border-border-accent hover:bg-bg-hover"
              } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div>{option}</div>
              {feedback && selectedOption === option && feedback.explanation && (
                <div
                  className={`mt-2 text-xs font-semibold font-body ${
                    feedback.correct ? "text-emerald-600" : "text-rose-600"
                  }`}
                >
                  {feedback.explanation}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

