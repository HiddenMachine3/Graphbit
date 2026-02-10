'use client';

import { useCallback, useEffect, useState } from "react";

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
import { useAppStore } from "../../lib/store";

export default function SessionContainer() {
  const [session, setSession] = useState<RevisionSessionDTO | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionDTO | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<RevisionFeedbackDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const currentProjectId = useAppStore((state) => state.currentProjectId);

  const handleStartSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    setFeedback(null);
    setAnswer("");
    setCompleted(false);
    try {
      if (!currentProjectId) {
        setError("Select a project to start a session");
        return;
      }
      const newSession = await startSession(currentProjectId);
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
  }, [currentProjectId]);

  const handleIDontKnow = useCallback(async () => {
    if (!session || !currentQuestion) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await submitAnswer(
        session.session_id,
        currentQuestion.id,
        ""
      );
      setFeedback(result);
      setAnsweredCount((count) => count + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit answer";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [currentQuestion, session]);

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
  }, [answer, currentQuestion, session, handleNextQuestion]);

  useEffect(() => {
    if (!feedback || !currentQuestion || currentQuestion.question_type !== "OPEN") {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleNextQuestion();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [feedback, currentQuestion, handleNextQuestion]);

  if (loading && !session) {
    return <Loading />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 shadow-[0_18px_45px_rgba(69,13,30,0.35)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-white">Revision Session</h1>
            <p className="text-sm text-slate-300">
              Adaptive recall guided by your knowledge graph
            </p>
          </div>
          <button
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-60"
            onClick={handleStartSession}
            disabled={loading}
          >
            {session ? "Restart Session" : "Start Session"}
          </button>
        </div>
      </div>

      <SessionProgress
        answeredCount={answeredCount}
        maxQuestions={session?.max_questions ?? null}
      />

      {error && <ErrorState message={error} />}

      {!session && !loading && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-6 text-sm text-slate-300">
          Start a session to receive questions.
        </div>
      )}

      {session && completed && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-6 text-sm text-slate-300">
          Session complete. You can restart to begin again.
        </div>
      )}

      {session && currentQuestion && (
        <div className="flex flex-col gap-4">
          <QuestionCard
            question={currentQuestion}
            selectedOption={
              currentQuestion.question_type === "MCQ" ? answer : undefined
            }
            onOptionSelect={
              currentQuestion.question_type === "MCQ"
                ? setAnswer
                : undefined
            }
            disabled={loading}
            feedback={currentQuestion.question_type === "MCQ" ? feedback : null}
          />

          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur">
            {currentQuestion.question_type === "OPEN" && (
              <>
                <label className="text-sm font-medium text-slate-200">
                  Your answer
                </label>
                <AnswerInput
                  questionType={currentQuestion.question_type}
                  value={answer}
                  onChange={setAnswer}
                  onSubmit={handleSubmitAnswer}
                  disabled={loading || Boolean(feedback)}
                  autoFocus
                  focusKey={currentQuestion.id}
                />
              </>
            )}
            {!feedback && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-60"
                  onClick={handleSubmitAnswer}
                  disabled={loading || !answer.trim()}
                >
                  Submit Answer
                </button>
                <button
                  className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-500 disabled:opacity-60"
                  onClick={handleIDontKnow}
                  disabled={loading}
                >
                  I don't know
                </button>
              </div>
            )}
          </div>

          {feedback && currentQuestion.question_type === "MCQ" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <button
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-60"
                onClick={handleNextQuestion}
                disabled={loading}
              >
                Next Question
              </button>
            </div>
          )}

          {feedback && currentQuestion.question_type === "OPEN" && (
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
