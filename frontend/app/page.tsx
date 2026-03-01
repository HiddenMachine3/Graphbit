"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Play, X } from "lucide-react";
import KnowledgeGraphView from "../components/graph/KnowledgeGraphView";
import ActivityHeatmap from "../components/ActivityHeatmap";
import SessionContainer from "../components/session/SessionContainer";
import NodeDetailPanel from "../components/graph/NodeDetailPanel";
import GraphLegend from "../components/graph/GraphLegend";
import NodeManagementPanel from "../components/graph/NodeManagementPanel";
import EdgeManagementPanel from "../components/graph/EdgeManagementPanel";
import { fetchGraphSummary, deleteNode, bulkDeleteNodes } from "../lib/api/graph";
import { useAppStore } from "../lib/store";
import type { GraphNodeDTO, GraphSummaryDTO } from "../lib/types";

export default function HomePage() {
  const [summary, setSummary] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [clickModeActive, setClickModeActive] = useState(false);
  const [selectedNodesForEdge, setSelectedNodesForEdge] = useState<string[]>([]);
  const [deleteModeActive, setDeleteModeActive] = useState(false);
  const [selectedNodesForDelete, setSelectedNodesForDelete] = useState<string[]>([]);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [brightnessAttribute, setBrightnessAttribute] = useState<keyof GraphNodeDTO>("proven_knowledge_rating");
  const [showMaterials, setShowMaterials] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [activityCollapsed, setActivityCollapsed] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [graphFitTrigger, setGraphFitTrigger] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currentProjectId = useAppStore((state) => state.currentProjectId);
  const setIsQuestioningMode = useAppStore((state) => state.setIsQuestioningMode);
  const recallCollapsedBeforeSessionRef = useRef<boolean | null>(null);

  const loadGraph = useCallback(async () => {
    if (!currentProjectId) {
      setSummary(null);
      setSelectedNodeId(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchGraphSummary(currentProjectId);
      setSummary(data);
      setSelectedNodeId((current) => current ?? data.nodes[0]?.id ?? null);
    } catch (fetchError) {
      const message = fetchError instanceof Error ? fetchError.message : "Failed to load graph";
      setError(message);
      console.error("Failed to fetch graph data:", fetchError);
    } finally {
      setIsLoading(false);
    }
  }, [currentProjectId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    setIsQuestioningMode(sessionPanelOpen);
    if (sessionPanelOpen) {
      if (recallCollapsedBeforeSessionRef.current === null) {
        recallCollapsedBeforeSessionRef.current = activityCollapsed;
      }
      setActivityCollapsed(true);
      setSidebarCollapsed(true);
    } else if (recallCollapsedBeforeSessionRef.current !== null) {
      setActivityCollapsed(recallCollapsedBeforeSessionRef.current);
      recallCollapsedBeforeSessionRef.current = null;
    }
    setGraphFitTrigger((value) => value + 1);

    const delayedRefit = window.setTimeout(() => {
      setGraphFitTrigger((value) => value + 1);
    }, 260);

    return () => {
      setIsQuestioningMode(false);
      window.clearTimeout(delayedRefit);
    };
  }, [activityCollapsed, sessionPanelOpen, setIsQuestioningMode]);

  const visibleNodes = summary
    ? showMaterials
      ? summary.nodes
      : summary.nodes.filter((node) => node.node_type !== "material")
    : [];

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);

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
      setSidebarCollapsed(false);
    }
  };

  const handleNodeClick = (nodeId: string) => {
    if (deleteModeActive) {
      setDeleteError(null);
      const clickedNode = visibleNodes.find((node) => node.id === nodeId);
      if (!clickedNode || clickedNode.node_type === "material" || nodeId.startsWith("material:")) {
        setDeleteError("Material nodes cannot be deleted");
        return;
      }
      setSelectedNodesForDelete((prev) => {
        if (prev.includes(nodeId)) {
          return prev.filter((id) => id !== nodeId);
        }
        return [...prev, nodeId];
      });
      return;
    }

    if (clickModeActive) {
      setSelectedNodesForEdge((prev) => {
        if (prev.includes(nodeId)) {
          return prev.filter((id) => id !== nodeId);
        }
        if (prev.length < 2) {
          return [...prev, nodeId];
        }
        return prev;
      });
      return;
    }

    setSelectedNodeId(nodeId);
    setSidebarCollapsed(false);
  };

  const handleDeleteSingleNode = async (nodeId: string) => {
    if (!currentProjectId) {
      setDeleteError("Select a project first");
      return;
    }

    if (!window.confirm("Delete this node? This will remove its edges and references.")) {
      return;
    }

    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await deleteNode(currentProjectId, nodeId);
      setSelectedNodesForDelete((prev) => prev.filter((id) => id !== nodeId));
      setSelectedNodeId(null);
      await loadGraph();
    } catch (deleteNodeError) {
      setDeleteError(deleteNodeError instanceof Error ? deleteNodeError.message : "Failed to delete node");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    if (!currentProjectId) {
      setDeleteError("Select a project first");
      return;
    }
    if (selectedNodesForDelete.length === 0) {
      setDeleteError("Select at least one node to delete");
      return;
    }

    const message = `Delete ${selectedNodesForDelete.length} node(s)? This will remove their edges and references.`;
    if (!window.confirm(message)) {
      return;
    }

    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await bulkDeleteNodes(currentProjectId, selectedNodesForDelete);
      setSelectedNodeId(null);
      setSelectedNodesForDelete([]);
      setDeleteModeActive(false);
      await loadGraph();
    } catch (bulkDeleteError) {
      setDeleteError(bulkDeleteError instanceof Error ? bulkDeleteError.message : "Failed to delete nodes");
    } finally {
      setDeleteLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="font-body text-text-muted">Loading knowledge graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="font-body text-text-muted">{error}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="font-body text-text-muted">Failed to load graph data</div>
      </div>
    );
  }

  return (
    <div
      className={`grid h-full w-full overflow-hidden ${
        sessionPanelOpen ? "grid-cols-[1fr_50%]" : "grid-cols-1"
      }`}
    >
      <div className="relative min-w-0 flex-1">
        <div className="absolute inset-0">
        <KnowledgeGraphView
          nodes={visibleNodes}
          edges={visibleEdges}
          projectId={currentProjectId}
          selectedNodeId={clickModeActive || deleteModeActive ? null : selectedNodeId}
          onSelectNode={handleNodeClick}
          highlightedNodeIds={
            deleteModeActive
              ? selectedNodesForDelete
              : clickModeActive
                ? selectedNodesForEdge
                : undefined
          }
          brightnessAttribute={brightnessAttribute}
          onGraphUpdated={loadGraph}
          fitTrigger={graphFitTrigger}
        />
      </div>

      {!sessionPanelOpen && (
        <div className={`absolute right-0 top-0 z-20 h-full transition-all duration-200 ${sidebarCollapsed ? "w-0" : "w-[320px]"}`}>
          <button
            type="button"
            onClick={() => setSidebarCollapsed((value) => !value)}
            className="absolute left-0 top-6 z-20 h-10 w-6 -translate-x-full rounded-l-md border border-r-0 border-border-default bg-bg-surface text-sm font-semibold font-body text-text-secondary hover:bg-bg-hover"
            aria-label={sidebarCollapsed ? "Open graph sidebar" : "Collapse graph sidebar"}
            title={sidebarCollapsed ? "Open graph sidebar" : "Collapse graph sidebar"}
          >
            {sidebarCollapsed ? "<" : ">"}
          </button>

          {!sidebarCollapsed && (
            <div className="h-full overflow-y-auto border-l border-border-default bg-bg-surface p-4">
              <div className="flex flex-col gap-4">
                <NodeDetailPanel
                  node={selectedNode}
                  onEdit={handleEditClick}
                  onDelete={handleDeleteSingleNode}
                />

                {editingNodeId === selectedNodeId ? (
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
                ) : (
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
                  onClickModeChange={(value) => {
                    setClickModeActive(value);
                    if (value) {
                      setDeleteModeActive(false);
                      setSelectedNodesForDelete([]);
                    }
                  }}
                  selectedNodesForEdge={selectedNodesForEdge}
                  onNodesChange={setSelectedNodesForEdge}
                />

                <div className="rounded-2xl border border-border-default bg-bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold font-heading text-text-primary">Delete Nodes</h3>
                      <p className="text-xs font-normal font-body text-text-muted">
                        Select multiple nodes in the graph, then delete them
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setDeleteError(null);
                        setDeleteModeActive((value) => {
                          const next = !value;
                          if (next) {
                            setClickModeActive(false);
                            setSelectedNodesForEdge([]);
                          } else {
                            setSelectedNodesForDelete([]);
                          }
                          return next;
                        });
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full border transition ${
                        deleteModeActive
                          ? "border-pkr-low/70 bg-pkr-low/20"
                          : "border-border-default bg-bg-elevated"
                      }`}
                      aria-pressed={deleteModeActive}
                    >
                      <span
                        className={`inline-block h-5 w-5 transform rounded-full bg-white/90 transition ${
                          deleteModeActive ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3 text-xs font-body text-text-secondary">
                    <span>{selectedNodesForDelete.length} selected</span>
                    <button
                      type="button"
                      onClick={handleBulkDelete}
                      disabled={deleteLoading || selectedNodesForDelete.length === 0}
                      className="rounded border border-border-default bg-bg-elevated px-3 py-1 font-semibold text-text-primary hover:bg-bg-hover disabled:opacity-60"
                    >
                      Delete selected
                    </button>
                  </div>
                  {deleteError && (
                    <div className="mt-2 rounded border border-pkr-low/30 bg-pkr-low/10 p-2 text-xs font-body text-pkr-low">
                      {deleteError}
                    </div>
                  )}
                </div>

                <div className="rounded-2xl border border-border-default bg-bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold font-heading text-text-primary">Materials</h3>
                      <p className="text-xs font-normal font-body text-text-muted">Show materials linked to nodes</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowMaterials((value) => !value)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full border transition ${
                        showMaterials
                          ? "border-accent/70 bg-accent/30"
                          : "border-border-default bg-bg-elevated"
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

                <div className="rounded-2xl border border-border-default bg-bg-surface p-4">
                  <h3 className="font-semibold font-heading text-text-primary">Node Brightness</h3>
                  <select
                    value={brightnessAttribute}
                    onChange={(event) => setBrightnessAttribute(event.target.value as keyof GraphNodeDTO)}
                    className="mt-2 w-full rounded border border-border-default bg-bg-elevated px-2 py-1 text-xs font-body text-text-primary focus:border-accent-dim"
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
          )}
        </div>
      )}

      {!sessionPanelOpen && (
        <div className="absolute bottom-4 left-4 z-30 w-[265px] max-w-[calc(100vw-2rem)]">
          <ActivityHeatmap
            className="w-full"
            collapsed={activityCollapsed}
            onToggleCollapse={() => setActivityCollapsed((value) => !value)}
          />
        </div>
      )}

      <div className="pointer-events-none absolute bottom-0 left-1/2 z-40 -translate-x-1/2">
        <div className="pointer-events-auto rounded-t-2xl border border-b-0 border-border-default bg-bg-surface px-4 pb-3 pt-2 shadow-lg">
          <button
            type="button"
            onClick={() => setSessionPanelOpen((value) => !value)}
            className={`flex items-center gap-2 rounded-lg border border-border-default border-b-4 px-5 py-2 text-sm font-semibold font-body text-white transition ${
              sessionPanelOpen
                ? "bg-pkr-low hover:bg-pkr-low/90"
                : "bg-accent hover:bg-accent-hover"
            }`}
          >
            {sessionPanelOpen ? <X className="h-4 w-4" /> : <Play className="h-4 w-4 fill-white" />}
            <span>{sessionPanelOpen ? "Stop Session" : "Start Session"}</span>
          </button>
        </div>
      </div>
      </div>

      {sessionPanelOpen && (
        <div className="h-full min-w-0 border-l border-border-default bg-bg-surface">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-border-default px-4 py-3">
              <h2 className="text-base font-semibold font-heading text-text-primary">Session</h2>
              <button
                type="button"
                onClick={() => setSessionPanelOpen(false)}
                className="rounded border border-border-default bg-bg-elevated px-2 py-1 text-sm font-semibold font-body text-text-primary hover:bg-bg-hover"
                aria-label="Close session panel"
              >
                ✕
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-hidden p-4">
              <SessionContainer autoStart hideStartButton />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
