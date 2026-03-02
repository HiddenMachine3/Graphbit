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
import { fetchMaterial, listMaterials } from "../lib/api/material";
import { useAppStore } from "../lib/store";
import type { GraphNodeDTO, GraphSummaryDTO, MaterialDTO } from "../lib/types";

function extractYoutubeVideoId(url: string): string | null {
  const rawInput = (url || "").trim();
  const input = /^https?:\/\//i.test(rawInput) ? rawInput : `https://${rawInput}`;
  if (!input) {
    return null;
  }

  try {
    const parsed = new URL(input);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.replace(/^\/+/, "");

    if ((host === "youtu.be" || host === "www.youtu.be") && path) {
      return path.split("/")[0] || null;
    }

    if (
      host === "youtube.com" ||
      host === "www.youtube.com" ||
      host === "m.youtube.com" ||
      host === "music.youtube.com" ||
      host === "youtube-nocookie.com" ||
      host === "www.youtube-nocookie.com"
    ) {
      if (path === "watch") {
        return parsed.searchParams.get("v") || parsed.searchParams.get("vi") || null;
      }
      if (path.startsWith("shorts/") || path.startsWith("embed/")) {
        return path.split("/")[1] || null;
      }
      if (path.startsWith("live/")) {
        return path.split("/")[1] || null;
      }
    }
  } catch {
    // fall through to regex fallback
  }

  const regexFallbacks = [
    /(?:youtube\.com\/watch\?.*?[?&]v=)([\w-]{11})/i,
    /(?:youtube\.com\/(?:embed|shorts|live)\/)([\w-]{11})/i,
    /(?:youtu\.be\/)([\w-]{11})/i,
    /(?:^|[^\w-])([\w-]{11})(?:[^\w-]|$)/,
  ];

  for (const pattern of regexFallbacks) {
    const match = rawInput.match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }

  return null;
}

function toYoutubeEmbedUrl(url: string): string | null {
  const videoId = extractYoutubeVideoId(url);
  if (!videoId) {
    return null;
  }
  return `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0`;
}

function getNodeYoutubeSourceInfo(
  node: GraphNodeDTO | null | undefined,
  materialsById: Record<string, MaterialDTO>
): {
  isValid: boolean;
  materialId: string | null;
  sourceUrl: string | null;
  videoId: string | null;
  embedUrl: string | null;
  candidateMaterialIds: string[];
} {
  if (!node) {
    return {
      isValid: false,
      materialId: null,
      sourceUrl: null,
      videoId: null,
      embedUrl: null,
      candidateMaterialIds: [],
    };
  }

  const candidateMaterialIds = new Set<string>(node.source_material_ids || []);
  if (node.id.startsWith("material:")) {
    candidateMaterialIds.add(node.id.replace("material:", ""));
  }

  for (const materialId of candidateMaterialIds) {
    const sourceUrl = materialsById[materialId]?.source_url || null;
    if (!sourceUrl) {
      continue;
    }

    const videoId = extractYoutubeVideoId(sourceUrl);
    if (!videoId) {
      continue;
    }

    const embedUrl = toYoutubeEmbedUrl(sourceUrl);
    if (!embedUrl) {
      continue;
    }

    return {
      isValid: true,
      materialId,
      sourceUrl,
      videoId,
      embedUrl,
      candidateMaterialIds: Array.from(candidateMaterialIds),
    };
  }

  return {
    isValid: false,
    materialId: null,
    sourceUrl: null,
    videoId: null,
    embedUrl: null,
    candidateMaterialIds: Array.from(candidateMaterialIds),
  };
}

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
  const [glowReach, setGlowReach] = useState(1.6);
  const [glowLightness, setGlowLightness] = useState(1.6);
  const [glowWhiteLiftCap, setGlowWhiteLiftCap] = useState(0.55);
  const [glowAlphaCap, setGlowAlphaCap] = useState(1.0);
  const [glowEnabled, setGlowEnabled] = useState(true);
  const [nodeFillOpacity, setNodeFillOpacity] = useState(0.8);
  const [visualSettingsOpen, setVisualSettingsOpen] = useState(false);
  const [showMaterials, setShowMaterials] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [activityCollapsed, setActivityCollapsed] = useState(false);
  const [sessionPanelOpen, setSessionPanelOpen] = useState(false);
  const [materialsById, setMaterialsById] = useState<Record<string, MaterialDTO>>({});
  const [activeVideoEmbedUrl, setActiveVideoEmbedUrl] = useState<string | null>(null);
  const [activeVideoTitle, setActiveVideoTitle] = useState<string>("");
  const [activeReadTitle, setActiveReadTitle] = useState<string>("");
  const [activeReadChunks, setActiveReadChunks] = useState<string[]>([]);
  const [activeReadTranscriptChunks, setActiveReadTranscriptChunks] = useState<string[]>([]);
  const [isReadLoading, setIsReadLoading] = useState(false);
  const [readError, setReadError] = useState<string | null>(null);
  const [graphFitTrigger, setGraphFitTrigger] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currentProjectId = useAppStore((state) => state.currentProjectId);
  const setIsQuestioningMode = useAppStore((state) => state.setIsQuestioningMode);
  const recallCollapsedBeforeSessionRef = useRef<boolean | null>(null);

  const loadGraph = useCallback(async () => {
    if (!currentProjectId) {
      setSummary(null);
      setMaterialsById({});
      setSelectedNodeId(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [data, materials] = await Promise.all([
        fetchGraphSummary(currentProjectId),
        listMaterials(currentProjectId),
      ]);
      setSummary(data);
      setMaterialsById(
        Object.fromEntries(materials.map((material) => [material.id, material]))
      );
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

  const materialSourceUrlById = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(materialsById).map(([id, material]) => [id, material?.source_url ?? null])
      ),
    [materialsById]
  );

  const selectedNode: GraphNodeDTO | null =
    visibleNodes.find((node) => node.id === selectedNodeId) ?? null;

  const selectedNodeYoutubeInfo = useMemo(
    () => getNodeYoutubeSourceInfo(selectedNode, materialsById),
    [selectedNode, materialsById]
  );

  const selectedNodeYoutubeEmbedUrl = useMemo(() => {
    if (!selectedNode) {
      return null;
    }

    if (selectedNode.node_type !== "chapter" && selectedNode.node_type !== "material") {
      return null;
    }

    return selectedNodeYoutubeInfo.embedUrl;
  }, [selectedNode, selectedNodeYoutubeInfo]);

  const selectedNodeYoutubeThumbnailUrl = useMemo(() => {
    if (!selectedNodeYoutubeInfo.videoId) {
      return null;
    }
    return `https://img.youtube.com/vi/${encodeURIComponent(selectedNodeYoutubeInfo.videoId)}/mqdefault.jpg`;
  }, [selectedNodeYoutubeInfo.videoId]);

  const selectedNodeVideoActionLabel =
    selectedNode?.node_type === "material" ? "View" : "Watch";

  const shouldShowMissingYoutubeHint =
    Boolean(selectedNode) &&
    (selectedNode?.node_type === "material" || selectedNode?.node_type === "chapter") &&
    !selectedNodeYoutubeEmbedUrl;

  const openSelectedVideo = useCallback(() => {
    if (!selectedNodeYoutubeEmbedUrl || !selectedNode) {
      return;
    }
    setActiveVideoEmbedUrl(selectedNodeYoutubeEmbedUrl);
    setActiveVideoTitle(selectedNode.topic_name);
  }, [selectedNodeYoutubeEmbedUrl, selectedNode]);

  const closeVideoPlayer = useCallback(() => {
    setActiveVideoEmbedUrl(null);
    setActiveVideoTitle("");
  }, []);

  const closeReadViewer = useCallback(() => {
    setActiveReadTitle("");
    setActiveReadChunks([]);
    setActiveReadTranscriptChunks([]);
    setReadError(null);
    setIsReadLoading(false);
  }, []);

  const handleOpenMaterialRead = useCallback(
    async ({ materialId, nodeTitle }: { materialId: string; nodeId: string; nodeTitle: string }) => {
      if (!materialId) {
        return;
      }

      setIsReadLoading(true);
      setReadError(null);
      setActiveReadTitle(nodeTitle || "Material Notes");
      setActiveReadChunks([]);
      setActiveReadTranscriptChunks([]);

      try {
        const material = await fetchMaterial(materialId);
        setActiveReadTitle(material.title || nodeTitle || "Material Notes");
        setActiveReadChunks(Array.isArray(material.chunks) ? material.chunks : []);
        setActiveReadTranscriptChunks(
          Array.isArray(material.transcript_chunks) ? material.transcript_chunks : []
        );
      } catch (materialError) {
        setReadError(
          materialError instanceof Error ? materialError.message : "Failed to load material notes"
        );
      } finally {
        setIsReadLoading(false);
      }
    },
    []
  );

  const handleOpenNodeVideo = useCallback(
    ({ nodeTitle, embedUrl }: { nodeId: string; nodeTitle: string; embedUrl: string }) => {
      if (!embedUrl) {
        return;
      }
      setActiveVideoEmbedUrl(embedUrl);
      setActiveVideoTitle(nodeTitle || "YouTube Video");
    },
    []
  );

  const debugNodeVideoResolution = useCallback(
    (node: GraphNodeDTO | null | undefined) => {
      if (!node) {
        console.log("[Graphbit][NodeClick] Node not found");
        return;
      }

      const youtubeInfo = getNodeYoutubeSourceInfo(node, materialsById);

      const candidateMaterialIds = new Set<string>(node.source_material_ids || []);
      if (node.id.startsWith("material:")) {
        candidateMaterialIds.add(node.id.replace("material:", ""));
      }

      const materialDebugRows = Array.from(candidateMaterialIds).map((materialId) => {
        const sourceUrl = materialsById[materialId]?.source_url || null;
        const videoId = sourceUrl ? extractYoutubeVideoId(sourceUrl) : null;
        const embedUrl = sourceUrl ? toYoutubeEmbedUrl(sourceUrl) : null;
        return {
          materialId,
          sourceUrl,
          videoId,
          hasEmbedUrl: Boolean(embedUrl),
        };
      });

      console.groupCollapsed(`[Graphbit][NodeClick] ${node.id} (${node.node_type ?? "unknown"})`);
      console.log("node", {
        id: node.id,
        nodeType: node.node_type,
        topic: node.topic_name,
        sourceMaterialIds: node.source_material_ids || [],
      });
      console.log("hasValidYoutubeSource", youtubeInfo.isValid);
      console.log("youtubeSourceInfo", youtubeInfo);
      console.log("materialsById keys", Object.keys(materialsById));
      console.table(materialDebugRows);
      const firstResolvable = materialDebugRows.find((row) => row.hasEmbedUrl);
      console.log("resolvedEmbedUrl", firstResolvable ? toYoutubeEmbedUrl(firstResolvable.sourceUrl || "") : null);
      console.groupEnd();
    },
    [materialsById]
  );

  const handleEditClick = () => {
    if (selectedNodeId) {
      setEditingNodeId(selectedNodeId);
      setSidebarCollapsed(false);
    }
  };

  const handleNodeClick = (nodeId: string) => {
    const clickedNode = visibleNodes.find((node) => node.id === nodeId);
    debugNodeVideoResolution(clickedNode);

    if (deleteModeActive) {
      setDeleteError(null);
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
          materialSourceUrlById={materialSourceUrlById}
          projectId={currentProjectId}
          selectedNodeId={clickModeActive || deleteModeActive ? null : selectedNodeId}
          onSelectNode={handleNodeClick}
          onOpenMaterialRead={handleOpenMaterialRead}
          onOpenNodeVideo={handleOpenNodeVideo}
          highlightedNodeIds={
            deleteModeActive
              ? selectedNodesForDelete
              : clickModeActive
                ? selectedNodesForEdge
                : undefined
          }
          brightnessAttribute={brightnessAttribute}
          glowReach={glowReach}
          glowLightness={glowLightness}
          glowWhiteLiftCap={glowWhiteLiftCap}
          glowAlphaCap={glowAlphaCap}
          glowEnabled={glowEnabled}
          nodeFillOpacity={nodeFillOpacity}
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
            <div className="flex h-full flex-col border-l border-border-default bg-bg-surface p-4">
              <div className="min-h-0 flex-1 overflow-y-auto">
                <div className="flex flex-col gap-4">
                <NodeDetailPanel
                  node={selectedNode}
                  onEdit={handleEditClick}
                  onDelete={handleDeleteSingleNode}
                  onWatch={selectedNodeYoutubeEmbedUrl ? openSelectedVideo : undefined}
                  watchLabel={selectedNodeVideoActionLabel}
                  thumbnailUrl={selectedNodeYoutubeThumbnailUrl}
                />

                {shouldShowMissingYoutubeHint && (
                  <div className="rounded-2xl border border-border-default bg-bg-surface p-3 text-xs font-body text-text-muted">
                    No valid YouTube source link resolved from associated source materials for this node.
                  </div>
                )}

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

              <div className="mt-4 rounded-2xl border border-border-default bg-bg-surface p-4">
                <button
                  type="button"
                  onClick={() => setVisualSettingsOpen((value) => !value)}
                  className="flex w-full items-center justify-between text-left"
                  aria-expanded={visualSettingsOpen}
                >
                  <h3 className="font-semibold font-heading text-text-primary">Visual Settings</h3>
                  <span className="text-xs font-body text-text-muted">{visualSettingsOpen ? "Hide" : "Show"}</span>
                </button>

                {visualSettingsOpen && (
                  <div className="mt-4 space-y-4">
                    <div className="rounded-lg border border-border-default bg-bg-elevated px-3 py-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Glow Enabled</span>
                        <button
                          type="button"
                          onClick={() => setGlowEnabled((value) => !value)}
                          className={`relative inline-flex h-5 w-10 items-center rounded-full border transition ${
                            glowEnabled
                              ? "border-accent/70 bg-accent/30"
                              : "border-border-default bg-bg-surface"
                          }`}
                          aria-pressed={glowEnabled}
                          aria-label="Toggle graph glow"
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white/90 transition ${
                              glowEnabled ? "translate-x-5" : "translate-x-0.5"
                            }`}
                          />
                        </button>
                      </div>
                    </div>

                    <div className={!glowEnabled ? "opacity-50" : ""}>
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Glow Reach</span>
                        <span className="text-xs font-body text-text-muted">{glowReach.toFixed(1)}x</span>
                      </div>
                      <input
                        type="range"
                        min={0.4}
                        max={3.5}
                        step={0.1}
                        value={glowReach}
                        onChange={(event) => setGlowReach(Number(event.target.value))}
                        disabled={!glowEnabled}
                        className="mt-2 w-full accent-accent"
                        aria-label="Adjust graph glow reach"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Glow Lightness</span>
                        <span className="text-xs font-body text-text-muted">{glowLightness.toFixed(1)}x</span>
                      </div>
                      <input
                        type="range"
                        min={0.4}
                        max={3.5}
                        step={0.1}
                        value={glowLightness}
                        onChange={(event) => setGlowLightness(Number(event.target.value))}
                        disabled={!glowEnabled}
                        className="mt-2 w-full accent-accent"
                        aria-label="Adjust graph glow lightness"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Node Fill Opacity</span>
                        <span className="text-xs font-body text-text-muted">{Math.round(nodeFillOpacity * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min={0.25}
                        max={1}
                        step={0.05}
                        value={nodeFillOpacity}
                        onChange={(event) => setNodeFillOpacity(Number(event.target.value))}
                        className="mt-2 w-full accent-accent"
                        aria-label="Adjust graph node fill opacity"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Glow White Lift Cap</span>
                        <span className="text-xs font-body text-text-muted">{glowWhiteLiftCap.toFixed(2)}</span>
                      </div>
                      <input
                        type="range"
                        min={0.2}
                        max={1.2}
                        step={0.05}
                        value={glowWhiteLiftCap}
                        onChange={(event) => setGlowWhiteLiftCap(Number(event.target.value))}
                        disabled={!glowEnabled}
                        className="mt-2 w-full accent-accent"
                        aria-label="Adjust glow white lift cap"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold font-body text-text-primary">Glow Alpha Cap</span>
                        <span className="text-xs font-body text-text-muted">{glowAlphaCap.toFixed(2)}</span>
                      </div>
                      <input
                        type="range"
                        min={0.2}
                        max={1.5}
                        step={0.05}
                        value={glowAlphaCap}
                        onChange={(event) => setGlowAlphaCap(Number(event.target.value))}
                        disabled={!glowEnabled}
                        className="mt-2 w-full accent-accent"
                        aria-label="Adjust glow alpha cap"
                      />
                    </div>
                    </div>
                  </div>
                )}
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

      {activeVideoEmbedUrl && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-5xl overflow-hidden rounded-2xl border border-border-default bg-bg-surface shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-default px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold font-heading text-text-primary">
                <Play className="h-4 w-4" />
                <span className="truncate">{activeVideoTitle || "YouTube Video"}</span>
              </div>
              <button
                type="button"
                onClick={closeVideoPlayer}
                className="rounded border border-border-default bg-bg-elevated p-1 text-text-secondary transition hover:bg-bg-hover hover:text-text-primary"
                aria-label="Close video player"
                title="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="aspect-video w-full bg-black">
              <iframe
                src={activeVideoEmbedUrl}
                title={activeVideoTitle || "YouTube player"}
                className="h-full w-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
              />
            </div>
          </div>
        </div>
      )}

      {(isReadLoading || Boolean(readError) || activeReadChunks.length > 0 || activeReadTranscriptChunks.length > 0) && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/70 p-4">
          <div className="flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-border-default bg-bg-surface shadow-2xl">
            <div className="flex items-center justify-between border-b border-border-default px-4 py-3">
              <div className="truncate text-sm font-semibold font-heading text-text-primary">
                {activeReadTitle || "Material Notes"}
              </div>
              <button
                type="button"
                onClick={closeReadViewer}
                className="rounded border border-border-default bg-bg-elevated p-1 text-text-secondary transition hover:bg-bg-hover hover:text-text-primary"
                aria-label="Close material notes"
                title="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm font-body text-text-secondary">
              {isReadLoading && <div className="text-text-muted">Loading notes...</div>}
              {!isReadLoading && readError && (
                <div className="rounded border border-pkr-low/30 bg-pkr-low/10 p-3 text-pkr-low">{readError}</div>
              )}
              {!isReadLoading && !readError && activeReadTranscriptChunks.length > 0 && (
                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Transcript</div>
                  <div className="space-y-3">
                    {activeReadTranscriptChunks.map((chunk, index) => (
                      <p key={`transcript-${index}`} className="leading-relaxed text-text-secondary">
                        {chunk}
                      </p>
                    ))}
                  </div>
                </div>
              )}
              {!isReadLoading && !readError && activeReadChunks.length > 0 && (
                <div className={activeReadTranscriptChunks.length > 0 ? "mt-5" : ""}>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Notes</div>
                  <div className="space-y-3">
                    {activeReadChunks.map((chunk, index) => (
                      <p key={`chunk-${index}`} className="leading-relaxed text-text-secondary">
                        {chunk}
                      </p>
                    ))}
                  </div>
                </div>
              )}
              {!isReadLoading && !readError && activeReadTranscriptChunks.length === 0 && activeReadChunks.length === 0 && (
                <div className="text-text-muted">No notes available for this material.</div>
              )}
            </div>
          </div>
        </div>
      )}

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
