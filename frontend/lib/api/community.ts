import { apiFetch } from "./client";
import type {
  CommunityDTO,
  CommunityProgressDTO,
  LeaderboardEntryDTO,
} from "../types";

export async function listCommunities(): Promise<CommunityDTO[]> {
  return apiFetch<CommunityDTO[]>("/communities");
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
