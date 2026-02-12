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
import DeletePanel from "../../components/graph/DeletePanel";

export default function GraphPage() {
  const [summary, setSummary] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [clickModeActive, setClickModeActive] = useState(false);
  const [selectedNodesForEdge, setSelectedNodesForEdge] = useState<string[]>([]);
  const [deleteModeActive, setDeleteModeActive] = useState(false);
  const [selectedNodesForDelete, setSelectedNodesForDelete] = useState<string[]>([]);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [brightnessAttribute, setBrightnessAttribute] = useState<keyof GraphNodeDTO>('proven_knowledge_rating');
  const [activeTab, setActiveTab] = useState<'details' | 'add' | 'connect' | 'delete' | 'display'>('details');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectMainNodeMode, setSelectMainNodeMode] = useState(false);
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

  useEffect(() => {
    if (activeTab !== 'connect' && clickModeActive) {
      setClickModeActive(false);
      setSelectedNodesForEdge([]);
    }
    if (activeTab !== 'delete' && deleteModeActive) {
      setDeleteModeActive(false);
      setSelectedNodesForDelete([]);
    }
    if (activeTab !== 'add' && selectMainNodeMode) {
      setSelectMainNodeMode(false);
    }
  }, [activeTab, clickModeActive, deleteModeActive, selectMainNodeMode]);

  const selectedNode: GraphNodeDTO | null =
    summary?.nodes.find((node) => node.id === selectedNodeId) ?? null;

  const handleEditClick = () => {
    if (selectedNodeId) {
      setEditingNodeId(selectedNodeId);
      setActiveTab('add');
    }
  };

  const handleConnectModeChange = (active: boolean) => {
    setClickModeActive(active);
    if (active) {
      setSelectMainNodeMode(false);
      setDeleteModeActive(false);
      setSelectedNodesForDelete([]);
      setActiveTab('connect');
    }
  };

  const handleDeleteModeChange = (active: boolean) => {
    setDeleteModeActive(active);
    if (active) {
      setSelectMainNodeMode(false);
      setClickModeActive(false);
      setSelectedNodesForEdge([]);
      setActiveTab('delete');
    }
  };

  const handleSelectMainNodeRequest = () => {
    setSelectMainNodeMode(true);
    setClickModeActive(false);
    setDeleteModeActive(false);
    setSelectedNodesForEdge([]);
    setSelectedNodesForDelete([]);
    setActiveTab('add');
  };

  const handleNodeClick = (nodeId: string) => {
    if (selectMainNodeMode) {
      const node = summary?.nodes.find((item) => item.id === nodeId);
      if (node && node.id.startsWith('chapter_')) {
        setSelectedNodeId(nodeId);
        setSelectMainNodeMode(false);
      }
      return;
    }
    if (clickModeActive) {
      setSelectedNodesForEdge((prev) => {
        if (prev.includes(nodeId)) {
          return prev.filter((id) => id !== nodeId);
        } else if (prev.length < 2) {
          return [...prev, nodeId];
        }
        return prev;
      });
    } else if (deleteModeActive) {
      setSelectedNodesForDelete((prev) => {
        if (prev.includes(nodeId)) {
          return prev.filter((id) => id !== nodeId);
        }
        return [...prev, nodeId];
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

      <div
        className={`grid gap-6 lg:items-start ${
          sidebarCollapsed
            ? 'lg:grid-cols-[minmax(0,1fr)]'
            : 'lg:grid-cols-[minmax(0,1fr)_280px]'
        }`}
      >
        <div className="relative">
          <KnowledgeGraphView
            nodes={summary.nodes}
            edges={summary.edges}
            projectId={currentProjectId}
            selectedNodeId={clickModeActive || deleteModeActive ? null : selectedNodeId}
            onSelectNode={handleNodeClick}
            onSelectEdge={setSelectedEdgeId}
            highlightedNodeIds={
              clickModeActive
                ? selectedNodesForEdge
                : deleteModeActive
                ? selectedNodesForDelete
                : undefined
            }
            brightnessAttribute={brightnessAttribute}
          />
          {sidebarCollapsed && (
            <button
              className="absolute right-3 top-3 rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1 text-xs text-slate-200 hover:bg-slate-900"
              onClick={() => setSidebarCollapsed(false)}
            >
              Show Panel
            </button>
          )}
        </div>

        {!sidebarCollapsed && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2">
              <div className="text-xs font-semibold text-slate-200">Controls</div>
              <button
                className="rounded bg-slate-900 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
                onClick={() => setSidebarCollapsed(true)}
              >
                Hide
              </button>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-2">
              <div className="grid grid-cols-5 gap-1">
              {[
                { id: 'details', label: 'Details' },
                { id: 'add', label: 'Add' },
                { id: 'connect', label: 'Connect' },
                { id: 'delete', label: 'Delete' },
                { id: 'display', label: 'Display' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  className={`rounded px-2 py-1 text-[11px] font-medium transition ${
                    activeTab === tab.id
                      ? 'bg-rose-600 text-white'
                      : 'bg-slate-900 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            </div>

            {activeTab === 'details' && (
              <NodeDetailPanel
                node={selectedNode}
                projectId={currentProjectId}
                onEdit={handleEditClick}
                onDeleted={() => {
                  setSelectedNodeId(null);
                  loadGraph();
                }}
              />
            )}

            {activeTab === 'add' && (
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
                selectingMainNode={selectMainNodeMode}
                onSelectMainNodeRequest={handleSelectMainNodeRequest}
              />
            )}

            {activeTab === 'connect' && (
              <EdgeManagementPanel
                nodes={summary.nodes}
                edges={summary.edges}
                selectedNodeId={selectedNodeId}
                projectId={currentProjectId}
                selectedEdgeId={selectedEdgeId}
                onEdgeDeleted={() => {
                  setSelectedEdgeId(null);
                  loadGraph();
                }}
                onEdgeCreated={() => {
                  setClickModeActive(false);
                  setSelectedNodesForEdge([]);
                  loadGraph();
                }}
                clickModeActive={clickModeActive}
                onClickModeChange={handleConnectModeChange}
                selectedNodesForEdge={selectedNodesForEdge}
                onNodesChange={setSelectedNodesForEdge}
              />
            )}

            {activeTab === 'delete' && (
              <DeletePanel
                nodes={summary.nodes}
                projectId={currentProjectId}
                deleteModeActive={deleteModeActive}
                onDeleteModeChange={handleDeleteModeChange}
                selectedNodeIds={selectedNodesForDelete}
                onSelectionChange={setSelectedNodesForDelete}
                onDeleted={() => {
                  setSelectedNodeId(null);
                  loadGraph();
                }}
              />
            )}

            {activeTab === 'display' && (
              <>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <h3 className="font-semibold text-white">Node Brightness</h3>
                  <select
                    value={brightnessAttribute}
                    onChange={(e) =>
                      setBrightnessAttribute(e.target.value as keyof GraphNodeDTO)
                    }
                    className="mt-2 w-full rounded border border-slate-700 bg-slate-950/50 px-2 py-1 text-xs text-slate-200"
                  >
                    <option value="proven_knowledge_rating">Proven Knowledge</option>
                    <option value="user_estimated_knowledge_rating">
                      User Estimated Knowledge
                    </option>
                    <option value="importance">Importance</option>
                    <option value="relevance">Relevance</option>
                    <option value="view_frequency">View Frequency</option>
                  </select>
                </div>
                <GraphLegend />
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
