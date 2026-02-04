import type { QuestionType } from "../../lib/types";

type AnswerInputProps = {
  questionType: QuestionType;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

export default function AnswerInput({
  questionType,
  value,
  onChange,
  disabled = false,
}: AnswerInputProps) {
  const commonClasses =
    "mt-3 w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400";

  if (questionType === "OPEN") {
    return (
      <textarea
        className={`${commonClasses} min-h-[120px]`}
        placeholder="Type your answer"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  return (
    <input
      className={commonClasses}
      placeholder={questionType === "MCQ" ? "Select or type option" : "Type your answer"}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
