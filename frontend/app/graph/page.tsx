"use client";

import { useEffect, useState, useCallback } from "react";

import { fetchGraphSummary } from "../../lib/api/graph";
import type { GraphSummaryDTO, GraphNodeDTO } from "../../lib/types";
import { useAppStore } from "../../lib/store";
import Loading from "../../components/Loading";
import ErrorState from "../../components/ErrorState";
import KnowledgeGraphView from "../../components/graph/KnowledgeGraphView";
import NodeDetailPanel from "../../components/graph/NodeDetailPanel";
import GraphLegend from "../../components/graph/GraphLegend";
import NodeManagementPanel from "../../components/graph/NodeManagementPanel";
import EdgeManagementPanel from "../../components/graph/EdgeManagementPanel";

export default function GraphPage() {
  const [summary, setSummary] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [clickModeActive, setClickModeActive] = useState(false);
  const [selectedNodesForEdge, setSelectedNodesForEdge] = useState<string[]>([]);
  const [brightnessAttribute, setBrightnessAttribute] = useState<keyof GraphNodeDTO>('proven_knowledge_rating');
  const [showMaterials, setShowMaterials] = useState(true);
  const currentProjectId = useAppStore((state) => state.currentProjectId);

  const loadGraph = useCallback(async () => {
    if (!currentProjectId) {
      setSummary(null);
      setSelectedNodeId(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchGraphSummary(currentProjectId);
      setSummary(data);
      setSelectedNodeId(data.nodes[0]?.id ?? null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load graph";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [currentProjectId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const visibleNodes = summary
    ? showMaterials
      ? summary.nodes
      : summary.nodes.filter((node) => node.node_type !== "material")
    : [];

  const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));

  useEffect(() => {
    if (!summary) {
      return;
    }

    if (selectedNodeId && visibleNodeIds.has(selectedNodeId)) {
      return;
    }

    setSelectedNodeId(visibleNodes[0]?.id ?? null);
  }, [summary, showMaterials, selectedNodeId, visibleNodes, visibleNodeIds]);

  const visibleEdges = summary
    ? showMaterials
      ? summary.edges
      : summary.edges.filter(
          (edge) =>
            edge.type !== "MATERIAL" &&
            visibleNodeIds.has(edge.source) &&
            visibleNodeIds.has(edge.target)
        )
    : [];

  const selectedNode: GraphNodeDTO | null =
    visibleNodes.find((node) => node.id === selectedNodeId) ?? null;

  const handleEditClick = () => {
    if (selectedNodeId) {
      setEditingNodeId(selectedNodeId);
    }
  };

  const handleNodeClick = (nodeId: string) => {
    if (clickModeActive) {
      setSelectedNodesForEdge((prev) => {
        if (prev.includes(nodeId)) {
          return prev.filter((id) => id !== nodeId);
        } else if (prev.length < 2) {
          return [...prev, nodeId];
        }
        return prev;
      });
    } else {
      setSelectedNodeId(nodeId);
    }
  };

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!summary) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-300">
        No graph data available.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
        <p className="text-sm text-slate-400">Visualized from backend graph data</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <KnowledgeGraphView
          nodes={visibleNodes}
          edges={visibleEdges}
          selectedNodeId={clickModeActive ? undefined : selectedNodeId}
          onSelectNode={handleNodeClick}
          highlightedNodeIds={clickModeActive ? selectedNodesForEdge : undefined}
          brightnessAttribute={brightnessAttribute}
        />
        <div className="flex flex-col gap-4">
          <NodeDetailPanel 
            node={selectedNode} 
            onEdit={handleEditClick}
          />
          {editingNodeId === selectedNodeId && (
            <NodeManagementPanel
              selectedNode={selectedNode}
              projectId={currentProjectId}
              onNodeCreated={() => {
                setEditingNodeId(null);
                loadGraph();
              }}
              onNodeUpdated={() => {
                setEditingNodeId(null);
                loadGraph();
              }}
            />
          )}
          {editingNodeId !== selectedNodeId && (
            <NodeManagementPanel
              selectedNode={null}
              projectId={currentProjectId}
              onNodeCreated={loadGraph}
              onNodeUpdated={loadGraph}
            />
          )}
          <EdgeManagementPanel
            nodes={visibleNodes}
            selectedNodeId={selectedNodeId}
            projectId={currentProjectId}
            onEdgeCreated={() => {
              setClickModeActive(false);
              setSelectedNodesForEdge([]);
              loadGraph();
            }}
            clickModeActive={clickModeActive}
            onClickModeChange={setClickModeActive}
            selectedNodesForEdge={selectedNodesForEdge}
            onNodesChange={setSelectedNodesForEdge}
          />
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white">Materials</h3>
                <p className="text-xs text-slate-400">Show materials linked to nodes</p>
              </div>
              <button
                type="button"
                onClick={() => setShowMaterials((value) => !value)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full border transition ${
                  showMaterials
                    ? "border-rose-500/70 bg-rose-600/30"
                    : "border-slate-700 bg-slate-900/60"
                }`}
                aria-pressed={showMaterials}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white/90 transition ${
                    showMaterials ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <h3 className="font-semibold text-white">Node Brightness</h3>
            <select
              value={brightnessAttribute}
              onChange={(e) => setBrightnessAttribute(e.target.value as keyof GraphNodeDTO)}
              className="mt-2 w-full rounded border border-slate-700 bg-slate-950/50 px-2 py-1 text-xs text-slate-200"
            >
              <option value="proven_knowledge_rating">Proven Knowledge</option>
              <option value="user_estimated_knowledge_rating">User Estimated Knowledge</option>
              <option value="importance">Importance</option>
              <option value="relevance">Relevance</option>
              <option value="view_frequency">View Frequency</option>
            </select>
          </div>
          <GraphLegend />
        </div>
      </div>
    </section>
  );
}
