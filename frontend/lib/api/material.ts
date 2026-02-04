import type {
  ContentSessionDTO,
  InterjectionDecisionDTO,
  QuestionDTO,
  RevisionFeedbackDTO,
} from "../types";

const DEMO_MODE = true;

const DEMO_MATERIAL = {
  title: "Binary Search – Conceptual Understanding",
  chunks: [
    "Binary search is a divide-and-conquer algorithm.",
    "It works on sorted arrays by repeatedly halving the search space.",
    "The time complexity of binary search is O(log n).",
    "Binary search relies on the invariant that the array is sorted.",
    "Incorrect mid calculation can cause overflow in some languages.",
  ],
};

const demoSessionProgress: Record<string, number> = {};

export async function startContentSession(
  materialId: string,
  userId: string
): Promise<ContentSessionDTO> {
  if (DEMO_MODE) {
    demoSessionProgress["demo-session"] = 0;
    return Promise.resolve({
      session_id: "demo-session",
      material_id: materialId,
      user_id: userId,
      started_at: new Date().toISOString(),
      last_interjection_at: null,
      consumed_chunks: 0,
    });
  }
  return Promise.resolve({
    session_id: `content-${materialId}-${userId}`,
    material_id: materialId,
    user_id: userId,
    started_at: new Date().toISOString(),
    last_interjection_at: null,
    consumed_chunks: 0,
  });
}

export async function fetchMaterial(materialId: string): Promise<{
  id: string;
  title: string;
  chunks: string[];
}> {
  if (DEMO_MODE) {
    return Promise.resolve({
      id: materialId,
      title: DEMO_MATERIAL.title,
      chunks: DEMO_MATERIAL.chunks,
    });
  }
  return Promise.resolve({
    id: materialId,
    title: "Material",
    chunks: [],
  });
}

export async function reportChunkConsumed(
  sessionId: string,
  consumedChunks: number
): Promise<ContentSessionDTO> {
  if (DEMO_MODE) {
    demoSessionProgress[sessionId] = consumedChunks;
    return Promise.resolve({
      session_id: sessionId,
      material_id: "demo-material",
      user_id: "demo-user",
      started_at: new Date().toISOString(),
      last_interjection_at: null,
      consumed_chunks: consumedChunks,
    });
  }
  return Promise.resolve({
    session_id: sessionId,
    material_id: "material-1",
    user_id: "user-1",
    started_at: new Date().toISOString(),
    last_interjection_at: null,
    consumed_chunks: consumedChunks,
  });
}

export async function shouldInterject(
  sessionId: string
): Promise<InterjectionDecisionDTO> {
  if (!sessionId) {
    return Promise.resolve({ should_interject: false });
  }
  if (DEMO_MODE) {
    const consumed = demoSessionProgress[sessionId] ?? 0;
    const should = consumed > 0 && consumed % 2 === 0;
    return Promise.resolve({
      should_interject: should,
      reason: "This question was asked to reinforce recent concepts.",
    });
  }
  return Promise.resolve({
    should_interject: false,
  });
}

export async function getInterjectionQuestion(
  sessionId: string
): Promise<QuestionDTO | null> {
  if (!sessionId) {
    return Promise.resolve(null);
  }
  if (DEMO_MODE) {
    return Promise.resolve({
      id: "q-demo-1",
      text: "What is the time complexity of binary search?",
      answer: "O(log n)",
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
      source_material_ids: ["demo-material"],
    });
  }
  return Promise.resolve({
    id: "interjection-question",
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
    source_material_ids: ["material-1"],
  });
}

export async function submitInterjectionAnswer(
  sessionId: string,
  questionId: string,
  answer: string
): Promise<RevisionFeedbackDTO> {
  if (!sessionId || !questionId) {
    return Promise.resolve({ correct: false, correct_answer: null });
  }
  if (DEMO_MODE) {
    return Promise.resolve({
      correct: true,
      correct_answer: "O(log n)",
      explanation: "Binary search halves the search space each step.",
    });
  }
  return Promise.resolve({
    correct: Boolean(answer && answer.length > 0),
    correct_answer: "A learning technique that involves retrieving information from memory.",
  });
}
