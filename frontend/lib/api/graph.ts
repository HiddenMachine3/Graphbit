import { apiFetch } from "./client";
import type { GraphSummaryDTO, NodeDTO, QuestionDTO } from "../types";

export async function listNodes(): Promise<NodeDTO[]> {
  return apiFetch<NodeDTO[]>("/graph/nodes");
}

export async function listQuestions(): Promise<QuestionDTO[]> {
  return apiFetch<QuestionDTO[]>("/graph/questions");
}

export async function fetchGraphSummary(): Promise<GraphSummaryDTO> {
  return apiFetch<GraphSummaryDTO>("/graph");
}

export async function createNode(
  topicName: string,
  importance: number = 0.5,
  relevance: number = 0.5
): Promise<NodeDTO> {
  return apiFetch<NodeDTO>("/graph/nodes", {
    method: "POST",
    body: JSON.stringify({
      topic_name: topicName,
      importance,
      relevance,
    }),
  });
}

export async function updateNode(
  nodeId: string,
  updates: Partial<{
    topic_name: string;
    proven_knowledge_rating: number;
    user_estimated_knowledge_rating: number;
    importance: number;
    relevance: number;
  }>
): Promise<NodeDTO> {
  return apiFetch<NodeDTO>(`/graph/nodes/${nodeId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function createEdge(
  fromNodeId: string,
  toNodeId: string,
  edgeType: string = "PREREQUISITE",
  weight: number = 1.0
): Promise<any> {
  return apiFetch(`/graph/edges`, {
    method: "POST",
    body: JSON.stringify({
      from_node_id: fromNodeId,
      to_node_id: toNodeId,
      edge_type: edgeType,
      weight,
    }),
  });
}
