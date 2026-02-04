import type {
  CommunityDTO,
  CommunityProgressDTO,
  LeaderboardEntryDTO,
} from "../types";

export async function listCommunities(): Promise<CommunityDTO[]> {
  return Promise.resolve([
    {
      id: "community-1",
      name: "Algorithms",
      description: "Core algorithmic foundations",
      node_importance_overrides: { "node-1": 1.2 },
    },
    {
      id: "community-2",
      name: "Systems",
      description: "Operating systems and low-level concepts",
      node_importance_overrides: { "node-2": 1.5 },
    },
  ]);
}

export async function setActiveCommunity(
  communityId: string
): Promise<{ community_id: string }>
{
  return Promise.resolve({ community_id: communityId });
}

export async function getCommunityProgress(
  communityId: string
): Promise<CommunityProgressDTO>
{
  return Promise.resolve({
    community_id: communityId,
    overall_progress: communityId === "community-1" ? 0.68 : 0.42,
    relevant_topics: communityId === "community-1" ? 12 : 8,
  });
}

export async function getLeaderboard(
  communityId: string
): Promise<LeaderboardEntryDTO[]>
{
  const base = communityId === "community-1" ? 0.8 : 0.6;
  return Promise.resolve([
    { user_id: "demo-user", score: base, rank: 1 },
    { user_id: "user-2", score: base - 0.1, rank: 2 },
    { user_id: "user-3", score: base - 0.2, rank: 3 },
  ]);
}
