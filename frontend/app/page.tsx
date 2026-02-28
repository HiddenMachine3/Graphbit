"use client";

import { useEffect, useMemo, useState } from "react";
import KnowledgeGraphView from "../components/graph/KnowledgeGraphView";
import ActivityHeatmap from "../components/ActivityHeatmap";
import { fetchGraphSummary } from "../lib/api/graph";
import { getCurrentUser } from "../lib/api/user";
import { useAppStore } from "../lib/store";
import type { GraphSummaryDTO, UserDTO } from "../lib/types";

export default function HomePage() {
  const [graphData, setGraphData] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<UserDTO | null>(null);
  const currentProjectId = useAppStore((state) => state.currentProjectId);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  }, []);

  useEffect(() => {
    let mounted = true;
    getCurrentUser()
      .then((user) => { if (mounted) setCurrentUser(user); })
      .catch(() => { if (mounted) setCurrentUser(null); });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!currentProjectId) {
      setGraphData(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    fetchGraphSummary(currentProjectId)
      .then((data) => {
        setGraphData(data);
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Failed to fetch graph data:", error);
        setIsLoading(false);
      });
  }, [currentProjectId]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="font-body text-text-muted">Loading knowledge graph...</div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="font-body text-text-muted">Failed to load graph data</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Dashboard Header */}
      <div className="w-full border-b border-border-default bg-bg-surface px-8 py-6">
        <h1 className="text-2xl font-bold font-heading text-text-primary">
          {greeting}, {currentUser?.name ?? currentUser?.username ?? "there"}
        </h1>
        <p className="mt-1 text-sm font-body text-text-secondary">
          Your knowledge queue is ready
          {/* TODO: wire due-for-review count from session queue endpoint */}
        </p>
      </div>

      <div className="flex flex-1 flex-col p-6">
        <div className="mb-4 flex-1">
          <KnowledgeGraphView
            nodes={graphData.nodes}
            edges={graphData.edges}
            projectId={currentProjectId}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
        </div>

        <div className="h-48">
          <ActivityHeatmap
            nodesCount={graphData.nodes.length}
            edgesCount={graphData.edges.length}
          />
        </div>
      </div>
    </div>
  );
}
