"use client";

import { useEffect, useState } from "react";
import KnowledgeGraphView from "../components/graph/KnowledgeGraphView";
import ActivityHeatmap from "../components/ActivityHeatmap";
import { fetchGraphSummary } from "../lib/api/graph";
import { useAppStore } from "../lib/store";
import type { GraphSummaryDTO } from "../lib/types";

export default function HomePage() {
  const [graphData, setGraphData] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const currentProjectId = useAppStore((state) => state.currentProjectId);

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
        <div className="text-slate-400">Loading knowledge graph...</div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-slate-400">Failed to load graph data</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col p-6">
      <div className="mb-6 flex-1">
        <KnowledgeGraphView
          nodes={graphData.nodes}
          edges={graphData.edges}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
      </div>

      <div className="h-64">
        <ActivityHeatmap
          nodesCount={graphData.nodes.length}
          edgesCount={graphData.edges.length}
        />
      </div>
    </div>
  );
}
