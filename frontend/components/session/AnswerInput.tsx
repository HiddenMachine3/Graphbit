import type { QuestionType } from "../../lib/types";

type AnswerInputProps = {
  questionType: QuestionType;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  disabled?: boolean;
};

export default function AnswerInput({
  questionType,
  value,
  onChange,
  onSubmit,
  disabled = false,
}: AnswerInputProps) {
  const commonClasses =
    "mt-3 w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift), allow Shift+Enter for newlines
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.();
    }
  };

  if (questionType === "OPEN") {
    return (
      <textarea
        className={`${commonClasses} min-h-[120px]`}
        placeholder="Type your answer (press Enter to submit, Shift+Enter for newline)"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
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
