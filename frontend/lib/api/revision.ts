import { apiFetch } from "./client";
import type { QuestionDTO, RevisionFeedbackDTO, RevisionSessionDTO } from "../types";

export async function startSession(projectId: string): Promise<RevisionSessionDTO> {
  return apiFetch<RevisionSessionDTO>("/revision/sessions", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function getNextQuestion(
  sessionId: string
): Promise<QuestionDTO | null> {
  if (!sessionId) {
    return null;
  }
  try {
    return await apiFetch<QuestionDTO>(`/revision/sessions/${sessionId}/next-question`);
  } catch {
    return null;
  }
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answer: string,
  performance?: "bad" | "ok" | "good" | "great"
): Promise<RevisionFeedbackDTO> {
  if (!sessionId || !questionId) {
    return { correct: false, correct_answer: null };
  }
  return apiFetch<RevisionFeedbackDTO>(`/revision/sessions/${sessionId}/submit-answer`, {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, answer, performance }),
  });
}
