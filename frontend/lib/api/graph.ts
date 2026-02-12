import { apiFetch } from "./client";
import type { GraphSummaryDTO, NodeDTO, QuestionDTO } from "../types";

export async function listNodes(projectId: string): Promise<NodeDTO[]> {
  return apiFetch<NodeDTO[]>(`/graph/nodes?project_id=${encodeURIComponent(projectId)}`);
}

export async function listQuestions(projectId: string): Promise<QuestionDTO[]> {
  return apiFetch<QuestionDTO[]>(`/graph/questions?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchGraphSummary(projectId: string): Promise<GraphSummaryDTO> {
  return apiFetch<GraphSummaryDTO>(`/graph?project_id=${encodeURIComponent(projectId)}`);
}

export async function createNode(
  projectId: string,
  topicName: string,
  importance: number = 0,
  relevance: number = 0.5
): Promise<NodeDTO> {
  return apiFetch<NodeDTO>("/graph/nodes", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      topic_name: topicName,
      importance,
      relevance,
    }),
  });
}

export async function updateNode(
  projectId: string,
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
    body: JSON.stringify({
      project_id: projectId,
      ...updates,
    }),
  });
}

export async function createEdge(
  projectId: string,
  fromNodeId: string,
  toNodeId: string,
  edgeType: string = "PREREQUISITE",
  weight: number = 1.0
): Promise<any> {
  return apiFetch(`/graph/edges`, {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      from_node_id: fromNodeId,
      to_node_id: toNodeId,
      edge_type: edgeType,
      weight,
    }),
  });
}
