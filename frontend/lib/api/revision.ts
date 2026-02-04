import type { QuestionDTO, RevisionFeedbackDTO, RevisionSessionDTO } from "../types";

export async function startSession(): Promise<RevisionSessionDTO> {
  return Promise.resolve({
    session_id: "mock-session",
    max_questions: 10,
  });
}

export async function getNextQuestion(
  sessionId: string
): Promise<QuestionDTO | null> {
  if (!sessionId) {
    return Promise.resolve(null);
  }
  return Promise.resolve({
    id: "mock-question",
    text: "What is active recall?",
    answer: "A learning technique that involves retrieving information from memory.",
    question_type: "OPEN",
    knowledge_type: "CONCEPT",
    covered_node_ids: ["node-1"],
    metadata: {
      created_by: "system",
      created_at: new Date().toISOString(),
      importance: 1,
      hits: 0,
      misses: 0,
    },
    difficulty: 3,
    tags: [],
    last_attempted_at: null,
    source_material_ids: [],
  });
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answer: string
): Promise<RevisionFeedbackDTO> {
  if (!sessionId || !questionId) {
    return Promise.resolve({ correct: false, correct_answer: null });
  }
  return Promise.resolve({
    correct: Boolean(answer && answer.length > 0),
    correct_answer: "A learning technique that involves retrieving information from memory.",
  });
}
