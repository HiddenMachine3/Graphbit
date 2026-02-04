import type { GraphSummaryDTO, NodeDTO, QuestionDTO } from "../types";

export async function listNodes(): Promise<NodeDTO[]> {
  return Promise.resolve([]);
}

export async function listQuestions(): Promise<QuestionDTO[]> {
  return Promise.resolve([]);
}

export async function fetchGraphSummary(): Promise<GraphSummaryDTO> {
  return Promise.resolve({
    nodes: [
      {
        id: "node-1",
        topic_name: "Active Recall",
        proven_knowledge_rating: 0.72,
        user_estimated_knowledge_rating: 0.7,
        importance: 0.9,
        relevance: 0.8,
        view_frequency: 4,
        source_material_ids: ["material-1"],
        forgetting_score: 0.3,
        linked_questions_count: 3,
        linked_materials_count: 1,
      },
      {
        id: "node-2",
        topic_name: "Spaced Repetition",
        proven_knowledge_rating: 0.45,
        user_estimated_knowledge_rating: 0.4,
        importance: 0.8,
        relevance: 0.7,
        view_frequency: 2,
        source_material_ids: ["material-2"],
        forgetting_score: 0.6,
        linked_questions_count: 2,
        linked_materials_count: 1,
      },
    ],
    edges: [
      {
        id: "edge-1",
        source: "node-1",
        target: "node-2",
        type: "PREREQUISITE",
        weight: 1,
      },
    ],
  });
}
