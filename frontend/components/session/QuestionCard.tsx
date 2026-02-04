import type { QuestionDTO } from "../../lib/types";

type QuestionCardProps = {
  question: QuestionDTO;
};

export default function QuestionCard({ question }: QuestionCardProps) {
  return (
    <div className="rounded border border-slate-200 bg-white p-6">
      <div className="text-xs uppercase tracking-wide text-slate-400">
        {question.question_type}
      </div>
      <h2 className="mt-2 text-lg font-semibold text-slate-900">
        {question.text}
      </h2>
    </div>
  );
}
