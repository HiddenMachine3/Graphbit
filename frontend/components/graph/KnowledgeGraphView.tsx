'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  addEdge,
  MiniMap,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type OnEdgesChange,
  type OnNodesChange,
  useReactFlow,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import type { GraphEdgeDTO, GraphNodeDTO } from "../../lib/types";
import { createEdge } from "../../lib/api/graph";
import GraphEdge from "./GraphEdge";
import GraphNode from "./GraphNode";
import MaterialNode from "./MaterialNode";
import useForceLayout from "../../lib/graph/useForceLayout";
import FABCluster from "../FABCluster";

export type KnowledgeGraphViewProps = {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
  materialSourceUrlById?: Record<string, string | null | undefined>;
  projectId: string | null;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  onOpenNodeVideo?: (payload: { nodeId: string; nodeTitle: string; embedUrl: string }) => void;
  highlightedNodeIds?: string[];
  brightnessAttribute?: keyof GraphNodeDTO;
  onGraphUpdated?: () => void;
  fitTrigger?: number;
};

const nodeTypes = { graphNode: GraphNode, materialNode: MaterialNode };
const edgeTypes = { graphEdge: GraphEdge };

function extractYoutubeVideoId(url: string): string | null {
  const rawInput = (url || "").trim();
  if (!rawInput) {
    return null;
  }

  const input = /^https?:\/\//i.test(rawInput) ? rawInput : `https://${rawInput}`;

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
      if (path.startsWith("shorts/") || path.startsWith("embed/") || path.startsWith("live/")) {
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
  ];

  for (const pattern of regexFallbacks) {
    const match = rawInput.match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }

  return null;
}

function toYoutubeThumbnailUrl(url: string): string | null {
  const videoId = extractYoutubeVideoId(url);
  if (!videoId) {
    return null;
  }
  return `https://img.youtube.com/vi/${encodeURIComponent(videoId)}/mqdefault.jpg`;
}

function buildFlowNodes(
  nodes: GraphNodeDTO[],
  brightnessAttribute: keyof GraphNodeDTO,
  materialSourceUrlById: Record<string, string | null | undefined>,
  expandedNodeIds: Set<string>,
  hasChildrenMap: Map<string, boolean>,
  onToggleExpand: (nodeId: string) => void,
  onOpenNodeVideo?: (payload: { nodeId: string; nodeTitle: string; embedUrl: string }) => void
): Node[] {
  return nodes.map((node) => {
    const candidateMaterialIds = new Set<string>(node.source_material_ids || []);
    if (node.id.startsWith("material:")) {
      candidateMaterialIds.add(node.id.replace("material:", ""));
    }

    let youtubeThumbnailUrl: string | null = null;
    let youtubeEmbedUrl: string | null = null;
    for (const materialId of candidateMaterialIds) {
      const sourceUrl = materialSourceUrlById[materialId];
      if (!sourceUrl) {
        continue;
      }
      const nextThumbnail = toYoutubeThumbnailUrl(sourceUrl);
      const nextEmbed = extractYoutubeVideoId(sourceUrl)
        ? `https://www.youtube.com/embed/${encodeURIComponent(extractYoutubeVideoId(sourceUrl) as string)}?autoplay=1&rel=0`
        : null;
      if (nextThumbnail && nextEmbed) {
        youtubeThumbnailUrl = nextThumbnail;
        youtubeEmbedUrl = nextEmbed;
        break;
      }
    }

    return {
      id: node.id,
      type: node.node_type === "material" ? "materialNode" : "graphNode",
      position: { x: 0, y: 0 },
      data: {
        ...node,
        brightnessAttribute,
        youtubeThumbnailUrl,
        youtubeEmbedUrl,
        isExpanded: expandedNodeIds.has(node.id),
        hasChildren: hasChildrenMap.get(node.id) || false,
        onToggleExpand,
        onOpenVideo:
          youtubeEmbedUrl && onOpenNodeVideo
            ? () =>
              onOpenNodeVideo({
                nodeId: node.id,
                nodeTitle: node.topic_name,
                embedUrl: youtubeEmbedUrl as string,
              })
            : undefined,
      },
      selected: false,
    };
  });
}

function buildFlowEdges(edges: GraphEdgeDTO[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: "graphEdge",
    data: { edgeType: edge.type },
  }));
}

export default function KnowledgeGraphView({
  nodes,
  edges,
  materialSourceUrlById,
  projectId,
  selectedNodeId,
  onSelectNode,
  onOpenNodeVideo,
  highlightedNodeIds,
  brightnessAttribute = "proven_knowledge_rating",
  onGraphUpdated,
  fitTrigger,
}: KnowledgeGraphViewProps) {
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());

  const handleToggleExpand = useCallback((nodeId: string) => {
    setExpandedNodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const { visibleNodes, visibleEdges, hasChildrenMap } = useMemo(() => {
    const inDegree = new Map<string, number>();
    const outEdges = new Map<string, string[]>();
    const nodeMap = new Map<string, GraphNodeDTO>();

    nodes.forEach(n => {
      inDegree.set(n.id, 0);
      outEdges.set(n.id, []);
      nodeMap.set(n.id, n);
    });

    edges.forEach(e => {
      if (inDegree.has(e.target)) {
        inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
      }
      if (outEdges.has(e.source)) {
        outEdges.get(e.source)!.push(e.target);
      }
    });

    const isVisible = new Set<string>();

    for (const [nodeId, degree] of inDegree.entries()) {
      if (degree === 0) {
        isVisible.add(nodeId);
      }
    }

    nodes.forEach(n => {
      if (n.node_type === 'material' || n.node_type === 'chapter') {
        isVisible.add(n.id);
      }
    });

    if (isVisible.size === 0 && nodes.length > 0) {
      isVisible.add(nodes[0].id);
    }

    const reachableFromDefault = new Set<string>(isVisible);
    const reachQueue = [...isVisible];
    while (reachQueue.length > 0) {
      const curr = reachQueue.shift()!;
      for (const child of (outEdges.get(curr) || [])) {
        if (!reachableFromDefault.has(child)) {
          reachableFromDefault.add(child);
          reachQueue.push(child);
        }
      }
    }

    for (const n of nodes) {
      if (!reachableFromDefault.has(n.id)) {
        isVisible.add(n.id);
        reachableFromDefault.add(n.id);
        const cycleQueue: string[] = [n.id];
        while (cycleQueue.length > 0) {
          const curr = cycleQueue.shift()!;
          for (const child of (outEdges.get(curr) || [])) {
            if (!reachableFromDefault.has(child)) {
              reachableFromDefault.add(child);
              cycleQueue.push(child);
            }
          }
        }
      }
    }

    const expandQueue = [...isVisible].filter(id => expandedNodeIds.has(id));
    while (expandQueue.length > 0) {
      const currentId = expandQueue.shift()!;
      const children = outEdges.get(currentId) || [];
      for (const childId of children) {
        if (!isVisible.has(childId)) {
          isVisible.add(childId);
          if (expandedNodeIds.has(childId)) {
            expandQueue.push(childId);
          }
        }
      }
    }

    const hasChildrenReturnMap = new Map<string, boolean>();
    nodes.forEach(n => {
      let hasHideableChildren = false;
      const children = outEdges.get(n.id) || [];
      for (const childId of children) {
        const childNode = nodeMap.get(childId);
        // We only consider a child "hideable" if it wouldn't be visible by default.
        if (childNode?.node_type !== 'material' && childNode?.node_type !== 'chapter' && inDegree.get(childId)! > 0) {
          hasHideableChildren = true;
          break;
        }
      }
      hasChildrenReturnMap.set(n.id, hasHideableChildren);
    });

    const finalNodes = nodes.filter(n => isVisible.has(n.id));
    const finalEdges = edges.filter(e => isVisible.has(e.source) && isVisible.has(e.target));

    return { visibleNodes: finalNodes, visibleEdges: finalEdges, hasChildrenMap: hasChildrenReturnMap };
  }, [nodes, edges, expandedNodeIds]);

  const sourceUrlById = materialSourceUrlById || {};
  const baseNodes = useMemo(
    () => buildFlowNodes(visibleNodes, brightnessAttribute, sourceUrlById, expandedNodeIds, hasChildrenMap, handleToggleExpand, onOpenNodeVideo),
    [visibleNodes, brightnessAttribute, sourceUrlById, expandedNodeIds, hasChildrenMap, handleToggleExpand, onOpenNodeVideo]
  );
  const baseEdges = useMemo(() => buildFlowEdges(visibleEdges), [visibleEdges]);
  const [flowNodes, setFlowNodes, onFlowNodesChange] = useNodesState(baseNodes);
  const [flowEdges, setFlowEdges, onFlowEdgesChange] = useEdgesState(baseEdges);
  const layoutNodes = useMemo(
    () => flowNodes.filter((node) => node.type !== "materialNode"),
    [flowNodes]
  );
  const layoutEdges = useMemo(
    () =>
      flowEdges.filter(
        (edge) => (edge.data as { edgeType?: string } | undefined)?.edgeType !== "MATERIAL"
      ),
    [flowEdges]
  );
  const initialRepulsionDoneRef = useRef(false);
  useEffect(() => {
    setFlowNodes((current) => {
      const baseNodeMap = new Map(baseNodes.map((node) => [node.id, node]));
      const currentMap = new Map(current.map((node) => [node.id, node]));

      const nextNodes = baseNodes.map((baseNode) => {
        const existingNode = currentMap.get(baseNode.id);
        if (existingNode) {
          return { ...existingNode, data: baseNode.data };
        }
        return baseNode;
      });

      return nextNodes;
    });
  }, [baseNodes, setFlowNodes]);

  useEffect(() => {
    setFlowNodes((current) =>
      current.map((node) => ({
        ...node,
        selected:
          highlightedNodeIds && highlightedNodeIds.length > 0
            ? highlightedNodeIds.includes(node.id)
            : node.id === selectedNodeId,
      }))
    );
  }, [selectedNodeId, highlightedNodeIds, setFlowNodes]);

  useEffect(() => {
    setFlowEdges(baseEdges);
  }, [baseEdges, setFlowEdges]);

  useEffect(() => {
    initialRepulsionDoneRef.current = false;
  }, [baseNodes.length]);

  const applyMaterialRepulsion = useCallback((current: Node[]) => {
    return current;
  }, []);

  const { onNodeDrag, onNodeDragEnd } = useForceLayout(
    layoutNodes,
    layoutEdges,
    setFlowNodes,
    applyMaterialRepulsion
  );

  useEffect(() => {
    if (initialRepulsionDoneRef.current) {
      return;
    }
    if (flowNodes.length === 0) {
      return;
    }
    initialRepulsionDoneRef.current = true;
    setFlowNodes((current) => applyMaterialRepulsion(current));
  }, [applyMaterialRepulsion, flowNodes.length, setFlowNodes]);
  const onConnect = useCallback(
    async (connection: Connection) => {
      if (!connection.source || !connection.target) {
        return;
      }
      if (!projectId) {
        console.error("Project id is required to create connections");
        return;
      }

      const sourceNode = flowNodes.find((node) => node.id === connection.source);
      const targetNode = flowNodes.find((node) => node.id === connection.target);
      const sourceIsMaterial = sourceNode?.type === "materialNode" || connection.source.startsWith("material:");
      const targetIsMaterial = targetNode?.type === "materialNode" || connection.target.startsWith("material:");

      if (sourceIsMaterial && targetIsMaterial) {
        console.error("Material to material connections are not supported");
        return;
      }

      if (sourceIsMaterial || targetIsMaterial) {
        try {
          const materialId = (sourceIsMaterial ? connection.source : connection.target).replace("material:", "");
          const nodeId = sourceIsMaterial ? connection.target : connection.source;
          const { attachMaterialNodes } = await import("../../lib/api/material");
          await attachMaterialNodes(materialId, [nodeId]);
          onGraphUpdated?.();
        } catch (error) {
          console.error("Failed to attach material node:", error);
        }
        return;
      }

      const edgePayload = {
        ...connection,
        type: "graphEdge",
      } as Edge;

      setFlowEdges((current) => addEdge(edgePayload, current));

      try {
        await createEdge(projectId, connection.source, connection.target, "APPLIED_WITH", 0.6);
      } catch (error) {
        console.error("Failed to create edge:", error);
        setFlowEdges((current) =>
          current.filter(
            (edge) =>
              !(edge.source === connection.source && edge.target === connection.target)
          )
        );
      }
    },
    [flowNodes, onGraphUpdated, projectId, setFlowEdges]
  );

  const handleNodesChange = useCallback(
    (changes: Parameters<typeof onFlowNodesChange>[0]) => {
      onFlowNodesChange(changes);
      let finishedDragging = false;

      changes.forEach((change) => {
        if (change.type === "position") {
          if (change.dragging === true && change.position) {
            onNodeDrag(change.id, change.position.x, change.position.y);
          } else if (change.dragging === false) {
            onNodeDragEnd(change.id);
            finishedDragging = true;
          }
        }
      });

      if (finishedDragging) {
        setFlowNodes((current) => applyMaterialRepulsion(current));
      }
    },
    [applyMaterialRepulsion, onFlowNodesChange, onNodeDrag, onNodeDragEnd, setFlowNodes]
  );

  return (
    <div className="h-full w-full rounded-lg border border-border-default bg-bg-base overflow-hidden relative">
      <ReactFlowProvider>
        <GraphFlowCanvas
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onFlowEdgesChange}
          onConnect={onConnect}
          onSelectNode={onSelectNode}
          onToggleExpand={handleToggleExpand}
          fitTrigger={fitTrigger}
        />
        <FABCluster />
      </ReactFlowProvider>
    </div>
  );
}

type GraphFlowCanvasProps = {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: (connection: Connection) => void;
  onSelectNode: (nodeId: string) => void;
  onToggleExpand: (nodeId: string) => void;
  fitTrigger?: number;
};

function GraphFlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onSelectNode,
  onToggleExpand,
  fitTrigger,
}: GraphFlowCanvasProps) {
  const { fitView } = useReactFlow();
  const fitTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (nodes.length > 0) {
      const handleFit = () => {
        fitView({ padding: 0.2, duration: 200 });
      };

      const frameA = requestAnimationFrame(() => {
        handleFit();
        requestAnimationFrame(handleFit);
      });

      window.addEventListener("resize", handleFit);
      return () => {
        window.removeEventListener("resize", handleFit);
        cancelAnimationFrame(frameA);
      };
    }
    return;
  }, [nodes.length, fitView]);

  useEffect(() => {
    if (nodes.length === 0) {
      return;
    }

    if (fitTimeoutRef.current) {
      window.clearTimeout(fitTimeoutRef.current);
    }

    fitTimeoutRef.current = window.setTimeout(() => {
      fitView({ padding: 0.2, duration: 200 });
    }, 250);

    return () => {
      if (fitTimeoutRef.current) {
        window.clearTimeout(fitTimeoutRef.current);
      }
    };
  }, [nodes.length, fitView]);

  useEffect(() => {
    if (nodes.length === 0) {
      return;
    }

    fitView({ padding: 0.2, duration: 250 });
  }, [fitTrigger, nodes.length, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, node) => {
        console.log("[Graphbit][GraphClick]", {
          id: node.id,
          type: node.type,
          data: node.data,
        });
        onSelectNode(node.id);
        if (node.data?.hasChildren) {
          onToggleExpand(node.id);
        }
      }}
      fitView
    >
      <MiniMap position="top-left" pannable zoomable />
    </ReactFlow>
  );
}
