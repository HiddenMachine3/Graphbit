import { apiFetch } from "./client";
import type {
  ContentSessionDTO,
  InterjectionDecisionDTO,
  MaterialDTO,
  QuestionDTO,
  RevisionFeedbackDTO,
} from "../types";

export async function listMaterials(projectId: string): Promise<MaterialDTO[]> {
  return apiFetch<MaterialDTO[]>(
    `/materials?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function createMaterial(
  projectId: string,
  title: string,
  contentText: string,
  createdBy?: string
): Promise<MaterialDTO> {
  return apiFetch<MaterialDTO>("/materials", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      title,
      content_text: contentText,
      created_by: createdBy,
    }),
  });
}

export async function deleteMaterial(materialId: string): Promise<void> {
  await apiFetch<void>(`/materials/${materialId}`, { method: "DELETE" });
}

export async function startContentSession(
  materialId: string,
  userId: string
): Promise<ContentSessionDTO> {
  return apiFetch<ContentSessionDTO>("/materials/sessions", {
    method: "POST",
    body: JSON.stringify({ material_id: materialId, user_id: userId }),
  });
}

export async function fetchMaterial(materialId: string): Promise<{
  id: string;
  title: string;
  chunks: string[];
}> {
  return apiFetch<{ id: string; title: string; chunks: string[] }>(
    `/materials/${materialId}`
  );
}

export async function reportChunkConsumed(
  sessionId: string,
  consumedChunks: number
): Promise<ContentSessionDTO> {
  return apiFetch<ContentSessionDTO>(
    `/materials/sessions/${sessionId}/report-chunk`,
    {
      method: "POST",
      body: JSON.stringify({ consumed_chunks: consumedChunks }),
    }
  );
}

export async function shouldInterject(
  sessionId: string
): Promise<InterjectionDecisionDTO> {
  if (!sessionId) {
    return { should_interject: false };
  }
  try {
    return await apiFetch<InterjectionDecisionDTO>(
      `/materials/sessions/${sessionId}/should-interject`
    );
  } catch {
    return { should_interject: false };
  }
}

export async function getInterjectionQuestion(
  sessionId: string
): Promise<QuestionDTO | null> {
  if (!sessionId) {
    return null;
  }
  try {
    return await apiFetch<QuestionDTO>(
      `/materials/sessions/${sessionId}/interjection-question`
    );
  } catch {
    return null;
  }
}

export async function submitInterjectionAnswer(
  sessionId: string,
  questionId: string,
  answer: string
): Promise<RevisionFeedbackDTO> {
  if (!sessionId || !questionId) {
    return { correct: false, correct_answer: null };
  }
  return apiFetch<RevisionFeedbackDTO>(
    `/materials/sessions/${sessionId}/submit-interjection`,
    {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer }),
    }
  );
}
