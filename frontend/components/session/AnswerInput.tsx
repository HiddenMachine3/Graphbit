import { useEffect, useRef } from "react";

import type { QuestionType } from "../../lib/types";

type AnswerInputProps = {
  questionType: QuestionType;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
  focusKey?: string | null;
};

export default function AnswerInput({
  questionType,
  value,
  onChange,
  onSubmit,
  disabled = false,
  autoFocus = false,
  focusKey = null,
}: AnswerInputProps) {
  const inputRef = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);
  const commonClasses =
    "mt-3 w-full rounded border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/60 disabled:cursor-not-allowed disabled:bg-slate-900/30 disabled:text-slate-400 disabled:opacity-80";

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus, questionType, focusKey]);

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
        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
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
      ref={inputRef as React.RefObject<HTMLInputElement>}
      className={commonClasses}
      placeholder={questionType === "MCQ" ? "Select or type option" : "Type your answer"}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
