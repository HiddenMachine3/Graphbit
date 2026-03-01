'use client';

import { useCallback, useEffect, useMemo, useRef } from "react";
import ReactFlow, {
  addEdge,
  Controls,
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
  const sourceUrlById = materialSourceUrlById || {};
  const baseNodes = useMemo(
    () => buildFlowNodes(nodes, brightnessAttribute, sourceUrlById, onOpenNodeVideo),
    [nodes, brightnessAttribute, sourceUrlById, onOpenNodeVideo]
  );
  const baseEdges = useMemo(() => buildFlowEdges(edges), [edges]);
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
      if (current.length === 0 || current.length !== baseNodes.length) {
        return baseNodes;
      }

      const baseNodeMap = new Map(baseNodes.map((node) => [node.id, node]));
      return current.map((node) => {
        const baseNode = baseNodeMap.get(node.id);
        if (!baseNode) {
          return node;
        }
        return {
          ...node,
          data: baseNode.data,
        };
      });
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
    const repulsors = current.filter((node) => node.type === "materialNode");
    if (repulsors.length === 0) {
      return current;
    }

    const minDistance = 200;
    const minNodeDistance = 120;
    const minMaterialDistance = 160;
    const minMaterialTopicDistance = 110;

    const unitVectorForPair = (aId: string, bId: string) => {
      const input = `${aId}|${bId}`;
      let hash = 0;
      for (let i = 0; i < input.length; i += 1) {
        hash = (hash * 31 + input.charCodeAt(i)) % 360;
      }
      const angle = (hash * Math.PI) / 180;
      return { x: Math.cos(angle), y: Math.sin(angle) };
    };

    const nextNodes = current.map((node) => ({
      ...node,
      position: {
        x: node.position?.x ?? 0,
        y: node.position?.y ?? 0,
      },
    }));

    const materialAdjusted = nextNodes.map((node) => {
      if (node.type === "materialNode") {
        return node;
      }

      let pushX = 0;
      let pushY = 0;
      const nodeX = node.position?.x ?? 0;
      const nodeY = node.position?.y ?? 0;

      repulsors.forEach((repulsor) => {
        const repX = repulsor.position?.x ?? 0;
        const repY = repulsor.position?.y ?? 0;
        const dx = nodeX - repX;
        const dy = nodeY - repY;
        const distance = Math.hypot(dx, dy) || 1;
        if (distance >= minDistance) {
          return;
        }
        const strength = (minDistance - distance) / distance;
        pushX += dx * strength;
        pushY += dy * strength;
      });

      if (pushX === 0 && pushY === 0) {
        return node;
      }

      return {
        ...node,
        position: {
          x: nodeX + pushX,
          y: nodeY + pushY,
        },
      };
    });

    const materialNodes = materialAdjusted.filter((node) => node.type === "materialNode");
    const topicNodes = materialAdjusted.filter((node) => node.type !== "materialNode");

    // Small-radius directional repulsion from material -> topic nodes,
    // with only slight counter-movement on material nodes.
    for (let i = 0; i < materialNodes.length; i += 1) {
      const materialNode = materialNodes[i];
      for (let j = 0; j < topicNodes.length; j += 1) {
        const topicNode = topicNodes[j];

        const mx = materialNode.position?.x ?? 0;
        const my = materialNode.position?.y ?? 0;
        const tx = topicNode.position?.x ?? 0;
        const ty = topicNode.position?.y ?? 0;

        let dx = mx - tx;
        let dy = my - ty;
        let distance = Math.hypot(dx, dy);

        if (distance < 1) {
          const unit = unitVectorForPair(materialNode.id, topicNode.id);
          dx = unit.x;
          dy = unit.y;
          distance = 1;
        }

        if (distance >= minMaterialTopicDistance) {
          continue;
        }

        const overlap = minMaterialTopicDistance - distance;
        const ux = dx / distance;
        const uy = dy / distance;

        const topicPush = overlap * 0.8;
        const materialPush = overlap * 0.2;

        materialNode.position = {
          x: mx + ux * materialPush,
          y: my + uy * materialPush,
        };
        topicNode.position = {
          x: tx - ux * topicPush,
          y: ty - uy * topicPush,
        };
      }
    }

    for (let i = 0; i < topicNodes.length; i += 1) {
      for (let j = i + 1; j < topicNodes.length; j += 1) {
        const a = topicNodes[i];
        const b = topicNodes[j];
        const ax = a.position?.x ?? 0;
        const ay = a.position?.y ?? 0;
        const bx = b.position?.x ?? 0;
        const by = b.position?.y ?? 0;
        let dx = bx - ax;
        let dy = by - ay;
        let distance = Math.hypot(dx, dy);
        if (distance < 1) {
          const unit = unitVectorForPair(a.id, b.id);
          dx = unit.x;
          dy = unit.y;
          distance = 1;
        }
        if (distance >= minNodeDistance) {
          continue;
        }
        const overlap = (minNodeDistance - distance) / 2;
        const ux = dx / distance;
        const uy = dy / distance;
        a.position = { x: ax - ux * overlap, y: ay - uy * overlap };
        b.position = { x: bx + ux * overlap, y: by + uy * overlap };
      }
    }

    for (let i = 0; i < materialNodes.length; i += 1) {
      for (let j = i + 1; j < materialNodes.length; j += 1) {
        const a = materialNodes[i];
        const b = materialNodes[j];
        const ax = a.position?.x ?? 0;
        const ay = a.position?.y ?? 0;
        const bx = b.position?.x ?? 0;
        const by = b.position?.y ?? 0;
        let dx = bx - ax;
        let dy = by - ay;
        let distance = Math.hypot(dx, dy);
        if (distance < 1) {
          const unit = unitVectorForPair(a.id, b.id);
          dx = unit.x;
          dy = unit.y;
          distance = 1;
        }
        if (distance >= minMaterialDistance) {
          continue;
        }
        const overlap = (minMaterialDistance - distance) / 2;
        const ux = dx / distance;
        const uy = dy / distance;
        a.position = { x: ax - ux * overlap, y: ay - uy * overlap };
        b.position = { x: bx + ux * overlap, y: by + uy * overlap };
      }
    }

    return materialAdjusted;
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
    <div className="h-full w-full rounded-lg border border-border-default bg-bg-base overflow-hidden">
      <ReactFlowProvider>
        <GraphFlowCanvas
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onFlowEdgesChange}
          onConnect={onConnect}
          onSelectNode={onSelectNode}
          fitTrigger={fitTrigger}
        />
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
  fitTrigger?: number;
};

function GraphFlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onSelectNode,
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
      }}
      fitView
    >
      <MiniMap position="top-left" pannable zoomable />
      <Controls position="top-left" style={{ marginTop: 8, marginLeft: 8 }} />
    </ReactFlow>
  );
}
