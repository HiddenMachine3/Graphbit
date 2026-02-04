'use client';

import { useState } from "react";

import type { QuestionDTO, RevisionFeedbackDTO } from "../../lib/types";
import QuestionCard from "../session/QuestionCard";
import AnswerInput from "../session/AnswerInput";
import FeedbackPanel from "../session/FeedbackPanel";
import Loading from "../Loading";

type InterjectionModalProps = {
  question: QuestionDTO;
  reason: string;
  onSubmit: (answer: string) => Promise<RevisionFeedbackDTO>;
  onResume: () => void;
};

export default function InterjectionModal({
  question,
  reason,
  onSubmit,
  onResume,
}: InterjectionModalProps) {
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<RevisionFeedbackDTO | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    const result = await onSubmit(answer);
    setFeedback(result);
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-2xl space-y-4 rounded bg-white p-6 shadow-xl">
        <div className="text-sm text-slate-600">{reason}</div>
        <QuestionCard question={question} />

        {loading && <Loading />}

        {!feedback && !loading && (
          <div className="rounded border border-slate-200 bg-white p-4">
            <label className="text-sm font-medium text-slate-700">Your answer</label>
            <AnswerInput
              questionType={question.question_type}
              value={answer}
              onChange={setAnswer}
            />
            <button
              className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
              onClick={handleSubmit}
              disabled={!answer.trim()}
            >
              Submit Answer
            </button>
          </div>
        )}

        {feedback && (
          <FeedbackPanel
            feedback={feedback}
            onNext={onResume}
          />
        )}
      </div>
    </div>
  );
}
