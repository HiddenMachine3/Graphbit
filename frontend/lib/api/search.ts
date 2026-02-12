import { apiFetch } from "./client";
import type { SearchResultsDTO } from "../types";

export async function searchKnowledge(
  projectId: string,
  query: string,
  limit: number = 10
): Promise<SearchResultsDTO> {
  return apiFetch<SearchResultsDTO>(
    `/search?project_id=${encodeURIComponent(projectId)}&q=${encodeURIComponent(query)}&limit=${limit}`
  );
}