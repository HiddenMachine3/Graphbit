import type { QuestionDTO } from "../../lib/types";

type QuestionCardProps = {
  question: QuestionDTO;
  selectedOption?: string;
  onOptionSelect?: (option: string) => void;
  disabled?: boolean;
};

export default function QuestionCard({
  question,
  selectedOption,
  onOptionSelect,
  disabled = false,
}: QuestionCardProps) {
  const isMCQ = question.question_type === "MCQ";

  return (
    <div className="rounded border border-slate-200 bg-white p-6">
      <div className="text-xs uppercase tracking-wide text-slate-400">
        {question.question_type}
      </div>
      <h2 className="mt-2 text-lg font-semibold text-slate-900">
        {question.text}
      </h2>

      {isMCQ && question.options && (
        <div className="mt-4 space-y-2">
          {question.options.map((option, index) => (
            <button
              key={index}
              onClick={() => onOptionSelect?.(option)}
              disabled={disabled}
              className={`w-full rounded border px-4 py-3 text-left text-sm font-medium transition-colors ${
                selectedOption === option
                  ? "border-slate-900 bg-slate-100 text-slate-900 ring-2 ring-slate-400"
                  : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
              } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

