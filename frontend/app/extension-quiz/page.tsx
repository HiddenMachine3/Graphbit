"use client";

import { useEffect, useMemo, useState } from "react";

import SharedQuestionAnswerPanel, {
  type SharedQAPair,
} from "@/components/quiz/SharedQuestionAnswerPanel";

type IncomingQuizMessage = {
  type: "GRAPHBIT_QUIZ_INIT";
  token: string;
  chunkIndex: number;
  totalChunks: number;
  qaPairs: Array<{ question?: string; answer?: string }>;
};

export default function ExtensionQuizPage() {
  const [token, setToken] = useState<string | null>(null);
  const [chunkIndex, setChunkIndex] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [pairs, setPairs] = useState<SharedQAPair[]>([]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data as IncomingQuizMessage | undefined;
      if (!data || data.type !== "GRAPHBIT_QUIZ_INIT") {
        return;
      }

      const nextPairs = Array.isArray(data.qaPairs)
        ? data.qaPairs
            .map((pair) => ({
              question: String(pair?.question ?? "").trim(),
              answer: String(pair?.answer ?? "").trim(),
            }))
            .filter((pair) => pair.question)
        : [];

      setToken(data.token);
      setChunkIndex(Number(data.chunkIndex || 0));
      setTotalChunks(Number(data.totalChunks || 0));
      setPairs(nextPairs);

      event.source?.postMessage(
        {
          type: "GRAPHBIT_QUIZ_READY",
          token: data.token,
        },
        { targetOrigin: "*" }
      );
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const subtitle = useMemo(() => {
    if (!totalChunks) {
      return "Waiting for quiz content from extension...";
    }
    return `Chunk ${chunkIndex + 1} of ${totalChunks}`;
  }, [chunkIndex, totalChunks]);

  const handleComplete = () => {
    if (token) {
      const targetWindow = window.opener ?? (window.parent !== window ? window.parent : null);
      targetWindow?.postMessage(
        {
          type: "GRAPHBIT_QUIZ_DONE",
          token,
        },
        "*"
      );
    }

    if (window.opener) {
      window.close();
    }
  };

  return (
    <main className="min-h-screen bg-transparent p-2">
      <SharedQuestionAnswerPanel
        pairs={pairs}
        title="Flashcard"
        subtitle={subtitle}
        onComplete={handleComplete}
      />
    </main>
  );
}
