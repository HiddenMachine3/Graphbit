import { apiFetch } from "./client";
import type { QuestionDTO } from "../types";

export async function listQuestions(projectId: string): Promise<QuestionDTO[]> {
  return apiFetch<QuestionDTO[]>(
    `/questions?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function createQuestion(payload: {
  project_id: string;
  text: string;
  answer: string;
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
