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
  createdBy?: string,
  sourceUrl?: string,
  transcriptText?: string,
  transcriptSegments?: Array<{ text: string; start?: number; duration?: number }>
): Promise<MaterialDTO & { imported_from_youtube?: boolean; youtube_video_id?: string | null; transcript_chunk_count?: number }> {
  return apiFetch<MaterialDTO & { imported_from_youtube?: boolean; youtube_video_id?: string | null; transcript_chunk_count?: number }>("/materials", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      title,
      content_text: contentText,
      transcript_text: transcriptText,
      transcript_segments: transcriptSegments,
      source_url: sourceUrl,
      link: sourceUrl,
      created_by: createdBy,
    }),
  });
}

export async function checkYoutubeTranscript(
  link: string
): Promise<{
  link: string;
  video_id: string | null;
  has_transcript: boolean;
  transcript_text: string;
  chunk_count: number;
  chunks: string[];
  segments: Array<{ text: string; start?: number; duration?: number }>;
}> {
  return apiFetch<{
    link: string;
    video_id: string | null;
    has_transcript: boolean;
    transcript_text: string;
    chunk_count: number;
    chunks: string[];
    segments: Array<{ text: string; start?: number; duration?: number }>;
  }>("/materials/youtube/transcript-check", {
    method: "POST",
    body: JSON.stringify({ link }),
  });
}

export async function deleteMaterial(materialId: string): Promise<void> {
  await apiFetch<void>(`/materials/${materialId}`, { method: "DELETE" });
}

export async function updateMaterial(
  materialId: string,
  updates: {
    title?: string;
    content_text?: string;
    source_url?: string;
    transcript_text?: string;
    transcript_segments?: Array<{ text: string; start?: number; duration?: number }>;
  }
): Promise<MaterialDTO> {
  return apiFetch<MaterialDTO>(`/materials/${materialId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function replaceMaterialNodes(
  materialId: string,
  nodeIds: string[],
  newNodes?: Array<{ title: string }>
): Promise<{ material_id: string; node_ids: string[]; created_node_ids?: string[] }> {
  return apiFetch<{ material_id: string; node_ids: string[]; created_node_ids?: string[] }>(
    `/materials/${materialId}/nodes`,
    {
      method: "PUT",
      body: JSON.stringify({ node_ids: nodeIds, new_nodes: newNodes }),
    }
  );
}

export async function suggestMaterialNodes(
  materialId: string,
  payload: {
    project_id: string;
    threshold: number;
    semantic_weight: number;
    keyword_weight: number;
    dedup_threshold: number;
    top_k: number;
  }
): Promise<{ strong: any[]; weak: any[] }> {
  return apiFetch(`/materials/${materialId}/suggestions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function suggestMaterialNodesByText(payload: {
  project_id: string;
  text: string;
  threshold: number;
  semantic_weight: number;
  keyword_weight: number;
  dedup_threshold: number;
  top_k: number;
}): Promise<{ strong: any[]; weak: any[] }> {
  return apiFetch(`/materials/suggestions/raw-text`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function attachMaterialNodes(
  materialId: string,
  nodeIds: string[]
): Promise<{ material_id: string; attached_nodes: number }> {
  return apiFetch<{ material_id: string; attached_nodes: number }>(
    `/materials/${materialId}/attach`,
    {
      method: "POST",
      body: JSON.stringify({ node_ids: nodeIds, question_ids: [] }),
    }
  );
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
  source_url?: string | null;
  chunks: string[];
  transcript_text?: string;
  transcript_chunks?: string[];
  transcript_segments?: Array<{ text: string; start?: number; duration?: number }>;
}> {
  return apiFetch<{
    id: string;
    title: string;
    source_url?: string | null;
    chunks: string[];
    transcript_text?: string;
    transcript_chunks?: string[];
    transcript_segments?: Array<{ text: string; start?: number; duration?: number }>;
  }>(
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
