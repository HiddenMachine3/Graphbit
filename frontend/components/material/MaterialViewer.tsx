'use client';

import { useCallback, useEffect, useMemo, useState } from "react";

import type { ContentSessionDTO, QuestionDTO } from "../../lib/types";
import {
  getInterjectionQuestion,
  reportChunkConsumed,
  shouldInterject,
  startContentSession,
  submitInterjectionAnswer,
} from "../../lib/api/material";
import Loading from "../Loading";
import ErrorState from "../ErrorState";
import ConsumeProgressBar from "./ConsumeProgressBar";
import InterjectionModal from "./InterjectionModal";

const DEFAULT_REASON = "This question was asked to reinforce recent concepts.";

type MaterialViewerProps = {
  materialId: string;
  userId: string;
  content: string;
};

export default function MaterialViewer({ materialId, userId, content }: MaterialViewerProps) {
  const chunks = useMemo(() => content.split("\n\n").filter(Boolean), [content]);
  const totalChunks = chunks.length;

  const [session, setSession] = useState<ContentSessionDTO | null>(null);
  const [currentChunkIndex, setCurrentChunkIndex] = useState(0);
  const [interjectionQuestion, setInterjectionQuestion] = useState<QuestionDTO | null>(null);
  const [interjectionReason, setInterjectionReason] = useState(DEFAULT_REASON);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    startContentSession(materialId, userId)
      .then((data) => {
        if (mounted) {
          setSession(data);
        }
      })
      .catch((err) => {
        if (mounted) {
          const message = err instanceof Error ? err.message : "Failed to start session";
          setError(message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [materialId, userId]);

  const handleConsume = useCallback(async () => {
    if (!session) {
      return;
    }
    if (currentChunkIndex >= totalChunks) {
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const consumedChunks = currentChunkIndex + 1;
      const updated = await reportChunkConsumed(session.session_id, consumedChunks);
      setSession(updated);
      setCurrentChunkIndex(consumedChunks);

      const decision = await shouldInterject(session.session_id);
      if (decision.should_interject) {
        setInterjectionReason(decision.reason || DEFAULT_REASON);
        const question = await getInterjectionQuestion(session.session_id);
        if (question) {
          setInterjectionQuestion(question);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to report consumption";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [session, currentChunkIndex, totalChunks]);

  const handleSubmitInterjection = useCallback(
    async (answer: string) => {
      if (!session || !interjectionQuestion) {
        return { correct: false, correct_answer: null };
      }
      return submitInterjectionAnswer(
        session.session_id,
        interjectionQuestion.id,
        answer
      );
    },
    [session, interjectionQuestion]
  );

  const handleResume = useCallback(() => {
    setInterjectionQuestion(null);
  }, []);

  if (loading && !session) {
    return <Loading />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Material Viewer</h1>
        <p className="text-sm text-slate-500">Consume content and receive interjections.</p>
      </div>

      {error && <ErrorState message={error} />}

      <ConsumeProgressBar consumed={currentChunkIndex} total={totalChunks} />

      <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-700">
        {chunks[currentChunkIndex] ?? "You have reached the end of this material."}
      </div>

      <button
        className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
        onClick={handleConsume}
        disabled={loading || currentChunkIndex >= totalChunks}
      >
        {currentChunkIndex >= totalChunks ? "Completed" : "Mark Chunk Read"}
      </button>

      {interjectionQuestion && (
        <InterjectionModal
          question={interjectionQuestion}
          reason={interjectionReason}
          onSubmit={handleSubmitInterjection}
          onResume={handleResume}
        />
      )}
    </div>
  );
}
