'use client';

import { useCallback, useEffect, useRef, useState } from "react";

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
import SharedQuestionAnswerPanel from "../quiz/SharedQuestionAnswerPanel";

type SessionContainerProps = {
  autoStart?: boolean;
  hideStartButton?: boolean;
};

export default function SessionContainer({
  autoStart = false,
  hideStartButton = false,
}: SessionContainerProps) {
  const [session, setSession] = useState<RevisionSessionDTO | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionDTO | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<RevisionFeedbackDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const currentProjectId = useAppStore((state) => state.currentProjectId);
  const autoStartAttemptedRef = useRef(false);
  const isEmbeddedMode = hideStartButton;

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

  const handleFlashcardPerformance = useCallback(
    async (performance: "bad" | "ok" | "good" | "great") => {
      if (!session || !currentQuestion) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await submitAnswer(
          session.session_id,
          currentQuestion.id,
          "",
          performance
        );
        setFeedback(result);
        setAnsweredCount((count) => count + 1);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to submit flashcard rating";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [currentQuestion, session]
  );

  useEffect(() => {
    if (!autoStart || autoStartAttemptedRef.current || session || loading) {
      return;
    }

    autoStartAttemptedRef.current = true;
    void handleStartSession();
  }, [autoStart, handleStartSession, loading, session]);

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

  const showFixedSubmitBar =
    isEmbeddedMode &&
    Boolean(session) &&
    Boolean(currentQuestion) &&
    !feedback &&
    currentQuestion?.question_type !== "FLASHCARD";

  return (
    <div className={`flex flex-col gap-6 ${isEmbeddedMode ? "h-full min-h-0" : ""}`}>
      <div className={isEmbeddedMode ? "min-h-0 flex-1 overflow-y-auto pr-1" : ""}>
      {!hideStartButton && (
        <div className="rounded-2xl border border-border-default bg-bg-surface p-5 shadow-[0_18px_45px_rgba(69,13,30,0.35)] backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold font-heading text-text-primary">Revision Session</h1>
              <p className="text-sm font-body text-text-secondary">
                Adaptive recall guided by your knowledge graph
              </p>
            </div>
            <button
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
              onClick={handleStartSession}
              disabled={loading}
            >
              {session ? "Restart Session" : "Start Session"}
            </button>
          </div>
        </div>
      )}

      <SessionProgress
        answeredCount={answeredCount}
        maxQuestions={session?.max_questions ?? null}
      />

      {error && <ErrorState message={error} />}

      {!session && !loading && (
        <div className="rounded-2xl border border-border-default bg-bg-surface p-6 text-sm font-body text-text-secondary">
          Start a session to receive questions.
        </div>
      )}

      {session && completed && (
        <div className="rounded-2xl border border-border-default bg-bg-surface p-6 text-sm font-body text-text-secondary">
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

          <div className="rounded-2xl border border-border-default bg-bg-surface p-6 backdrop-blur">
            {currentQuestion.question_type === "OPEN" && (
              <>
                <label className="text-sm font-medium font-body text-text-primary">
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
            {currentQuestion.question_type === "FLASHCARD" && (
              <SharedQuestionAnswerPanel
                pairs={[
                  {
                    question: currentQuestion.text,
                    answer: currentQuestion.answer,
                  },
                ]}
                title="FLASHCARD"
                subtitle="Rate your recall after revealing the answer"
                showPerformanceRating={!feedback}
                disabled={loading || Boolean(feedback)}
                onRatePerformance={(performance) => {
                  void handleFlashcardPerformance(performance);
                }}
              />
            )}
            {!feedback && !isEmbeddedMode && (
              <div className="mt-4 flex flex-wrap gap-2">
                {currentQuestion.question_type !== "FLASHCARD" ? (
                  <>
                    <button
                      className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
                      onClick={handleSubmitAnswer}
                      disabled={loading || !answer.trim()}
                    >
                      Submit Answer
                    </button>
                    <button
                      className="rounded-lg border border-border-default px-4 py-2 text-sm font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
                      onClick={handleIDontKnow}
                      disabled={loading}
                    >
                      I don't know
                    </button>
                  </>
                ) : null}
              </div>
            )}
          </div>

          {feedback && currentQuestion.question_type === "MCQ" && (
            <div className="rounded-2xl border border-border-default bg-bg-surface p-4">
              <button
                className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
                onClick={handleNextQuestion}
                disabled={loading}
              >
                Next Question
              </button>
            </div>
          )}

          {feedback && currentQuestion.question_type === "FLASHCARD" && (
            <div className="rounded-2xl border border-border-default bg-bg-surface p-4">
              <div className="mb-3 text-sm font-body text-text-secondary">
                Performance recorded: <span className="font-semibold text-text-primary">{feedback.performance ?? "ok"}</span>
              </div>
              <button
                className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
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

      {showFixedSubmitBar && (
        <div className="border-t border-border-default bg-bg-surface p-4">
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold font-body text-white transition hover:bg-accent-hover disabled:opacity-60"
              onClick={handleSubmitAnswer}
              disabled={loading || !answer.trim()}
            >
              Submit Answer
            </button>
            <button
              className="rounded-lg border border-border-default px-4 py-2 text-sm font-body text-text-primary transition hover:border-border-accent disabled:opacity-60"
              onClick={handleIDontKnow}
              disabled={loading}
            >
              I don't know
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
