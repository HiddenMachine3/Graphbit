import { apiFetch } from "./client";
import type {
  CommunityDTO,
  CommunityProgressDTO,
  LeaderboardEntryDTO,
} from "../types";

export async function listCommunities(): Promise<CommunityDTO[]> {
  return apiFetch<CommunityDTO[]>("/communities");
}

export async function createCommunity(payload: {
  name: string;
  description?: string;
  project_ids?: string[];
  member_ids?: string[];
  node_importance_overrides?: Record<string, Record<string, number>>;
  question_importance_overrides?: Record<string, Record<string, number>>;
  created_by?: string;
}): Promise<CommunityDTO> {
  return apiFetch<CommunityDTO>("/communities", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCommunity(
  communityId: string,
  payload: Partial<{
    name: string;
    description: string;
    project_ids: string[];
    member_ids: string[];
    node_importance_overrides: Record<string, Record<string, number>>;
    question_importance_overrides: Record<string, Record<string, number>>;
  }>
): Promise<CommunityDTO> {
  return apiFetch<CommunityDTO>(`/communities/${communityId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteCommunity(communityId: string): Promise<void> {
  await apiFetch<void>(`/communities/${communityId}`, { method: "DELETE" });
}

export async function setActiveCommunity(
  communityId: string
): Promise<{ community_id: string }>
{
  return apiFetch<{ community_id: string }>("/communities/active", {
    method: "POST",
    body: JSON.stringify({ community_id: communityId }),
  });
}

export async function getCommunityProgress(
  communityId: string
): Promise<CommunityProgressDTO>
{
  return apiFetch<CommunityProgressDTO>(`/communities/${communityId}/progress`);
}

export async function getLeaderboard(
  communityId: string
): Promise<LeaderboardEntryDTO[]>
{
  return apiFetch<LeaderboardEntryDTO[]>(`/communities/${communityId}/leaderboard`);
}
