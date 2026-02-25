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
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
      <div className="text-xs uppercase tracking-wide text-slate-400">
        {question.question_type}
      </div>
      <div className="mt-2 text-lg font-semibold text-white">
        <RichContent content={question.text} className="text-lg font-semibold text-white" />
      </div>

      {isMCQ && question.options && (
        <div className="mt-4 space-y-2">
          {question.options.map((option, index) => (
            <button
              key={index}
              onClick={() => onOptionSelect?.(option)}
              disabled={disabled}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm font-medium transition-colors ${
                selectedOption === option
                  ? "border-blue-500/60 bg-blue-500/15 text-white ring-2 ring-blue-400/40"
                  : "border-slate-700 bg-slate-950/35 text-slate-200 hover:border-slate-500 hover:bg-slate-900/55"
              } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div>{option}</div>
              {feedback && selectedOption === option && feedback.explanation && (
                <div
                  className={`mt-2 text-xs font-semibold ${
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

