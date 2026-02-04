"use client";

import { useEffect, useState, useCallback } from "react";

import { fetchGraphSummary } from "../../lib/api/graph";
import type { GraphSummaryDTO, GraphNodeDTO } from "../../lib/types";
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

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGraphSummary();
      setSummary(data);
      setSelectedNodeId(data.nodes[0]?.id ?? null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load graph";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const selectedNode: GraphNodeDTO | null =
    summary?.nodes.find((node) => node.id === selectedNodeId) ?? null;

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
      <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-500">
        No graph data available.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
        <p className="text-sm text-slate-500">Visualized from backend graph data</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <KnowledgeGraphView
          nodes={summary.nodes}
          edges={summary.edges}
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
              onNodeCreated={loadGraph}
              onNodeUpdated={loadGraph}
            />
          )}
          <EdgeManagementPanel
            nodes={summary.nodes}
            selectedNodeId={selectedNodeId}
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
          <div className="rounded border border-slate-200 bg-white p-4">
            <h3 className="font-semibold text-slate-900">Node Brightness</h3>
            <select
              value={brightnessAttribute}
              onChange={(e) => setBrightnessAttribute(e.target.value as keyof GraphNodeDTO)}
              className="mt-2 w-full rounded border border-slate-300 px-2 py-1 text-xs"
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
