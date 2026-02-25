import { apiFetch } from "./client";
import type { QuestionDTO } from "../types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function generateQuestionsFromText(payload: {
  text: string;
  n: number;
}): Promise<{ qa_pairs: Array<{ question: string; answer: string }> }> {
  return apiFetch<{ qa_pairs: Array<{ question: string; answer: string }> }>(
    "/qa/generate",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function importQuestionsFromFile(payload: {
  projectId: string;
  file: File;
  createdBy?: string;
}): Promise<{ imported_count: number; question_ids: string[] }> {
  const formData = new FormData();
  formData.append("project_id", payload.projectId);
  formData.append("file", payload.file);
  if (payload.createdBy) {
    formData.append("created_by", payload.createdBy);
  }

  const response = await fetch(`${BASE_URL}/questions/import`, {
    method: "POST",
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const message = data?.detail || data?.message || "Failed to import questions";
    throw new Error(message);
  }
  return data;
}

export async function previewQuestionsFromFile(payload: {
  file: File;
  offset?: number;
  limit?: number;
}): Promise<{
  total_count: number;
  preview_count: number;
  offset?: number;
  limit?: number;
  has_more?: boolean;
  questions: Array<{
    text: string;
    answer: string;
    question_type: string;
    difficulty: number;
    tags: string[];
  }>;
}> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (typeof payload.offset === "number") {
    formData.append("offset", String(payload.offset));
  }
  if (typeof payload.limit === "number") {
    formData.append("limit", String(payload.limit));
  }

  const response = await fetch(`${BASE_URL}/questions/import/preview`, {
    method: "POST",
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const message = data?.detail || data?.message || "Failed to preview questions";
    throw new Error(message);
  }
  return data;
}

export async function listQuestions(projectId: string): Promise<QuestionDTO[]> {
  return apiFetch<QuestionDTO[]>(
    `/questions?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function createQuestion(payload: {
  project_id: string;
  text: string;
  answer: string;
  options?: string[];
  option_explanations?: string[];
  question_type?: string;
  knowledge_type?: string;
  covered_node_ids?: string[];
  difficulty?: number;
  tags?: string[];
  source_material_ids?: string[];
  created_by?: string;
}): Promise<QuestionDTO> {
  return apiFetch<QuestionDTO>("/questions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteQuestion(questionId: string): Promise<void> {
  await apiFetch<void>(`/questions/${questionId}`, { method: "DELETE" });
}

export async function updateQuestion(
  questionId: string,
  updates: Partial<{
    text: string;
    answer: string;
    options: string[];
    option_explanations: string[];
    question_type: string;
    knowledge_type: string;
    covered_node_ids: string[];
    difficulty: number;
    tags: string[];
    source_material_ids: string[];
  }>
): Promise<QuestionDTO> {
  return apiFetch<QuestionDTO>(`/questions/${questionId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function replaceQuestionNodes(
  questionId: string,
  nodeIds: string[],
  newNodes?: Array<{ title: string }>
): Promise<{ question_id: string; node_ids: string[]; created_node_ids?: string[] }> {
  return apiFetch<{ question_id: string; node_ids: string[]; created_node_ids?: string[] }>(
    `/questions/${questionId}/nodes`,
    {
      method: "PUT",
      body: JSON.stringify({ node_ids: nodeIds, new_nodes: newNodes }),
    }
  );
}

export async function suggestQuestionNodes(
  questionId: string,
  payload: {
    project_id: string;
    threshold: number;
    semantic_weight: number;
    keyword_weight: number;
    dedup_threshold: number;
    top_k: number;
  }
): Promise<{ strong: any[]; weak: any[] }> {
  return apiFetch(`/questions/${questionId}/suggestions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function suggestQuestionNodesByText(payload: {
  project_id: string;
  text: string;
  threshold: number;
  semantic_weight: number;
  keyword_weight: number;
  dedup_threshold: number;
  top_k: number;
}): Promise<{ strong: any[]; weak: any[] }> {
  return apiFetch(`/questions/suggestions/raw-text`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
