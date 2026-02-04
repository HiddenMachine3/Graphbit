"use client";

import { useEffect, useState } from "react";

import {
  getCommunityProgress,
  getLeaderboard,
  listCommunities,
  setActiveCommunity,
} from "../../lib/api/community";
import type {
  CommunityDTO,
  CommunityProgressDTO,
  LeaderboardEntryDTO,
} from "../../lib/types";
import { useAppStore } from "../../lib/store";
import Loading from "../../components/Loading";
import ErrorState from "../../components/ErrorState";
import CommunitySwitcher from "../../components/communities/CommunitySwitcher";
import CommunityProgress from "../../components/communities/CommunityProgress";
import LeaderboardTable from "../../components/communities/LeaderboardTable";

const CURRENT_USER_ID = "demo-user";

export default function CommunitiesPage() {
  const [communities, setCommunities] = useState<CommunityDTO[]>([]);
  const [progress, setProgress] = useState<CommunityProgressDTO | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currentCommunityId = useAppStore((state) => state.currentCommunityId);
  const setCurrentCommunityId = useAppStore((state) => state.setCurrentCommunityId);
  const setCurrentCommunityName = useAppStore((state) => state.setCurrentCommunityName);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    listCommunities()
      .then((data) => {
        if (mounted) {
          setCommunities(data);
          if (!currentCommunityId && data.length > 0) {
            setCurrentCommunityId(data[0].id);
            setCurrentCommunityName(data[0].name);
          }
        }
      })
      .catch((err) => {
        if (mounted) {
          const message = err instanceof Error ? err.message : "Failed to load communities";
          setError(message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [currentCommunityId, setCurrentCommunityId, setCurrentCommunityName]);

  useEffect(() => {
    if (!currentCommunityId) {
      setProgress(null);
      setLeaderboard([]);
      return;
    }
    let mounted = true;
    Promise.all([
      getCommunityProgress(currentCommunityId),
      getLeaderboard(currentCommunityId),
    ])
      .then(([progressData, leaderboardData]) => {
        if (mounted) {
          setProgress(progressData);
          setLeaderboard(leaderboardData);
        }
      })
      .catch((err) => {
        if (mounted) {
          const message = err instanceof Error ? err.message : "Failed to load community data";
          setError(message);
        }
      });

    return () => {
      mounted = false;
    };
  }, [currentCommunityId]);

  const handleSelectCommunity = async (community: CommunityDTO) => {
    setLoading(true);
    setError(null);
    try {
      await setActiveCommunity(community.id);
      setCurrentCommunityId(community.id);
      setCurrentCommunityName(community.name);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to switch community";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && communities.length === 0) {
    return <Loading />;
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Communities</h1>
        <p className="text-sm text-slate-500">Switch active learning context</p>
      </div>

      {error && <ErrorState message={error} />}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <CommunitySwitcher
          communities={communities}
          activeCommunityId={currentCommunityId}
          onSelect={handleSelectCommunity}
          loading={loading}
        />
        <div className="flex flex-col gap-4">
          <CommunityProgress progress={progress} />
          <LeaderboardTable entries={leaderboard} currentUserId={CURRENT_USER_ID} />
        </div>
      </div>
    </section>
  );
}
