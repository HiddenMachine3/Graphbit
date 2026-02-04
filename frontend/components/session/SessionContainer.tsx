'use client';

import { useCallback, useState } from "react";

import type {
  QuestionDTO,
  RevisionFeedbackDTO,
  RevisionSessionDTO,
} from "../../lib/types";
import {
  getNextQuestion,
  startSession,
  submitAnswer,
} from "../../lib/api/revision";
import Loading from "../Loading";
import ErrorState from "../ErrorState";
import QuestionCard from "./QuestionCard";
import AnswerInput from "./AnswerInput";
import FeedbackPanel from "./FeedbackPanel";
import SessionProgress from "./SessionProgress";

export default function SessionContainer() {
  const [session, setSession] = useState<RevisionSessionDTO | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionDTO | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<RevisionFeedbackDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);

  const handleStartSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    setFeedback(null);
    setAnswer("");
    setCompleted(false);
    try {
      const newSession = await startSession();
      setSession(newSession);
      const next = await getNextQuestion(newSession.session_id);
      setCurrentQuestion(next);
      if (!next) {
        setCompleted(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start session";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSubmitAnswer = useCallback(async () => {
    if (!session || !currentQuestion) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await submitAnswer(
        session.session_id,
        currentQuestion.id,
        answer
      );
      setFeedback(result);
      setAnsweredCount((count) => count + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit answer";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [answer, currentQuestion, session]);

  const handleNextQuestion = useCallback(async () => {
    if (!session) {
      return;
    }
    setLoading(true);
    setError(null);
    setFeedback(null);
    setAnswer("");
    try {
      const next = await getNextQuestion(session.session_id);
      setCurrentQuestion(next);
      if (!next) {
        setCompleted(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load question";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [session]);

  if (loading && !session) {
    return <Loading />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Revision Session</h1>
          <p className="text-sm text-slate-500">
            Orchestrated by backend session engine
          </p>
        </div>
        <button
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
          onClick={handleStartSession}
          disabled={loading}
        >
          {session ? "Restart Session" : "Start Session"}
        </button>
      </div>

      <SessionProgress
        answeredCount={answeredCount}
        maxQuestions={session?.max_questions ?? null}
      />

      {error && <ErrorState message={error} />}

      {!session && !loading && (
        <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Start a session to receive questions.
        </div>
      )}

      {session && completed && (
        <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Session complete. You can restart to begin again.
        </div>
      )}

      {session && currentQuestion && (
        <div className="flex flex-col gap-4">
          <QuestionCard question={currentQuestion} />

          {!feedback && (
            <div className="rounded border border-slate-200 bg-white p-6">
              <label className="text-sm font-medium text-slate-700">
                Your answer
              </label>
              <AnswerInput
                questionType={currentQuestion.question_type}
                value={answer}
                onChange={setAnswer}
                disabled={loading}
              />
              <button
                className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
                onClick={handleSubmitAnswer}
                disabled={loading || !answer.trim()}
              >
                Submit Answer
              </button>
            </div>
          )}

          {feedback && (
            <FeedbackPanel
              feedback={feedback}
              onNext={handleNextQuestion}
              disabled={loading}
            />
          )}
        </div>
      )}
    </div>
  );
}
