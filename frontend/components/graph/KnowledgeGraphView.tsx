'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { GraphEdgeDTO, GraphNodeDTO } from "../../lib/types";

type KnowledgeGraphViewProps = {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
  materialSourceUrlById?: Record<string, string | null | undefined>;
  projectId: string | null;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  onOpenMaterialRead?: (payload: { materialId: string; nodeId: string; nodeTitle: string }) => void;
  onOpenNodeVideo?: (payload: { nodeId: string; nodeTitle: string; embedUrl: string }) => void;
  highlightedNodeIds?: string[];
  brightnessAttribute?: keyof GraphNodeDTO;
  glowReach?: number;
  glowLightness?: number;
  glowWhiteLiftCap?: number;
  glowAlphaCap?: number;
  glowEnabled?: boolean;
  nodeFillOpacity?: number;
  onGraphUpdated?: () => void;
  fitTrigger?: number;
};

type VisualNode = {
  id: string;
  label: string;
  type: "topic" | "material" | "chapter";
  brightnessValue: number;
  hasChildren: boolean;
  isExpanded: boolean;
  materialId: string | null;
  sourceUrl: string | null;
  youtubeEmbedUrl: string | null;
  youtubeThumbnailUrl: string | null;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
};

type VisualEdge = {
  id: string;
  source: string;
  target: string;
  edgeType: string;
};

type NodeProjection = {
  id: string;
  label: string;
  type: "topic" | "material" | "chapter";
  brightnessValue: number;
  hasChildren: boolean;
  isExpanded: boolean;
  materialId: string | null;
  sourceUrl: string | null;
  youtubeEmbedUrl: string | null;
  youtubeThumbnailUrl: string | null;
};

type HoverPreviewState = {
  nodeId: string;
  x: number;
  y: number;
  title: string;
  thumbnailUrl: string;
};

type GraphProjection = {
  nodes: NodeProjection[];
  edges: VisualEdge[];
};

type TransformState = {
  scale: number;
  offsetX: number;
  offsetY: number;
};

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

function resolveNodeProjection(
  nodes: GraphNodeDTO[],
  edges: GraphEdgeDTO[],
  brightnessAttribute: keyof GraphNodeDTO,
  materialSourceUrlById: Record<string, string | null | undefined>,
  expandedNodeIds: Set<string>
): GraphProjection {
  const inDegree = new Map<string, number>();
  const outEdges = new Map<string, string[]>();
  const nodeMap = new Map<string, GraphNodeDTO>();

  nodes.forEach((node) => {
    inDegree.set(node.id, 0);
    outEdges.set(node.id, []);
    nodeMap.set(node.id, node);
  });

  edges.forEach((edge) => {
    if (inDegree.has(edge.target)) {
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    }
    if (outEdges.has(edge.source)) {
      outEdges.get(edge.source)?.push(edge.target);
    }
  });

  const isVisible = new Set<string>();

  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      isVisible.add(nodeId);
    }
  }

  nodes.forEach((node) => {
    if (node.node_type === "material" || node.node_type === "chapter") {
      isVisible.add(node.id);
    }
  });

  if (isVisible.size === 0 && nodes.length > 0) {
    isVisible.add(nodes[0].id);
  }

  const reachableFromDefault = new Set<string>(isVisible);
  const reachQueue = [...isVisible];
  while (reachQueue.length > 0) {
    const current = reachQueue.shift() as string;
    for (const child of outEdges.get(current) || []) {
      if (!reachableFromDefault.has(child)) {
        reachableFromDefault.add(child);
        reachQueue.push(child);
      }
    }
  }

  for (const node of nodes) {
    if (!reachableFromDefault.has(node.id)) {
      isVisible.add(node.id);
      reachableFromDefault.add(node.id);
      const cycleQueue: string[] = [node.id];
      while (cycleQueue.length > 0) {
        const current = cycleQueue.shift() as string;
        for (const child of outEdges.get(current) || []) {
          if (!reachableFromDefault.has(child)) {
            reachableFromDefault.add(child);
            cycleQueue.push(child);
          }
        }
      }
    }
  }

  const expandQueue = [...isVisible].filter((id) => expandedNodeIds.has(id));
  while (expandQueue.length > 0) {
    const current = expandQueue.shift() as string;
    const children = outEdges.get(current) || [];
    for (const child of children) {
      if (!isVisible.has(child)) {
        isVisible.add(child);
        if (expandedNodeIds.has(child)) {
          expandQueue.push(child);
        }
      }
    }
  }

  const hasChildrenMap = new Map<string, boolean>();
  nodes.forEach((node) => {
    let hasHideableChildren = false;
    const children = outEdges.get(node.id) || [];
    for (const childId of children) {
      const childNode = nodeMap.get(childId);
      if (
        childNode?.node_type !== "material" &&
        childNode?.node_type !== "chapter" &&
        (inDegree.get(childId) || 0) > 0
      ) {
        hasHideableChildren = true;
        break;
      }
    }
    hasChildrenMap.set(node.id, hasHideableChildren);
  });

  const visibleNodes = nodes.filter((node) => isVisible.has(node.id));
  const visibleEdges = edges.filter((edge) => isVisible.has(edge.source) && isVisible.has(edge.target));

  const projectedNodes: NodeProjection[] = visibleNodes.map((node) => {
    const candidateMaterialIds = new Set<string>(node.source_material_ids || []);
    if (node.id.startsWith("material:")) {
      candidateMaterialIds.add(node.id.replace("material:", ""));
    }

    const materialIds = Array.from(candidateMaterialIds);
    let sourceUrl: string | null = null;
    let primaryMaterialId: string | null = materialIds[0] || null;
    let youtubeEmbedUrl: string | null = null;
    let youtubeThumbnailUrl: string | null = null;

    for (const materialId of materialIds) {
      const candidate = materialSourceUrlById[materialId];
      if (!candidate) {
        continue;
      }
      if (!primaryMaterialId) {
        primaryMaterialId = materialId;
      }
      if (!sourceUrl) {
        sourceUrl = candidate;
      }
      const videoId = extractYoutubeVideoId(candidate);
      if (videoId) {
        youtubeEmbedUrl = `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0`;
        youtubeThumbnailUrl = `https://img.youtube.com/vi/${encodeURIComponent(videoId)}/mqdefault.jpg`;
        break;
      }
    }

    const brightnessRaw = Number(node[brightnessAttribute]);
    const brightnessValue = Number.isFinite(brightnessRaw) ? Math.max(0, Math.min(1, brightnessRaw)) : 0;

    return {
      id: node.id,
      label: node.topic_name,
      type: node.node_type || "topic",
      brightnessValue,
      hasChildren: hasChildrenMap.get(node.id) || false,
      isExpanded: expandedNodeIds.has(node.id),
      materialId: primaryMaterialId,
      sourceUrl,
      youtubeEmbedUrl,
      youtubeThumbnailUrl,
    };
  });

  const projectedEdges: VisualEdge[] = visibleEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    edgeType: edge.type,
  }));

  return { nodes: projectedNodes, edges: projectedEdges };
}

function pkrColor(pkr: number): [number, number, number] {
  if (pkr >= 0.7) return [61, 184, 122];
  if (pkr >= 0.4) return [224, 148, 58];
  return [178, 52, 52];
}

function initialNodeRadius(type: "topic" | "material" | "chapter"): number {
  if (type === "material") return 16;
  if (type === "chapter") return 20;
  return 22;
}

function toVisualNodes(nextNodes: NodeProjection[], existingById: Map<string, VisualNode>): VisualNode[] {
  const total = Math.max(nextNodes.length, 1);

  return nextNodes.map((node, index) => {
    const previous = existingById.get(node.id);
    if (previous) {
      return {
        ...previous,
        label: node.label,
        type: node.type,
        brightnessValue: node.brightnessValue,
        hasChildren: node.hasChildren,
        isExpanded: node.isExpanded,
        materialId: node.materialId,
        sourceUrl: node.sourceUrl,
        youtubeEmbedUrl: node.youtubeEmbedUrl,
        youtubeThumbnailUrl: node.youtubeThumbnailUrl,
        radius: initialNodeRadius(node.type),
      };
    }

    const angle = (index / total) * Math.PI * 2;
    const distance = 180 + (index % 6) * 45;

    return {
      id: node.id,
      label: node.label,
      type: node.type,
      brightnessValue: node.brightnessValue,
      hasChildren: node.hasChildren,
      isExpanded: node.isExpanded,
      materialId: node.materialId,
      sourceUrl: node.sourceUrl,
      youtubeEmbedUrl: node.youtubeEmbedUrl,
      youtubeThumbnailUrl: node.youtubeThumbnailUrl,
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
      vx: 0,
      vy: 0,
      radius: initialNodeRadius(node.type),
    };
  });
}

function normalizeLabel(label: string): string {
  const trimmed = label.trim();
  if (trimmed.length <= 24) {
    return trimmed;
  }
  return `${trimmed.slice(0, 21)}...`;
}

export default function KnowledgeGraphView({
  nodes,
  edges,
  materialSourceUrlById,
  selectedNodeId,
  onSelectNode,
  onOpenMaterialRead,
  onOpenNodeVideo,
  highlightedNodeIds,
  brightnessAttribute = "proven_knowledge_rating",
  glowReach = 1,
  glowLightness = 1,
  glowWhiteLiftCap = 0.55,
  glowAlphaCap = 1,
  glowEnabled = true,
  nodeFillOpacity = 1,
  fitTrigger,
}: KnowledgeGraphViewProps) {
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());
  const [hoverPreview, setHoverPreview] = useState<HoverPreviewState | null>(null);

  const handleToggleExpand = useCallback((nodeId: string) => {
    setExpandedNodeIds((previous) => {
      const next = new Set(previous);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const projection = useMemo(
    () =>
      resolveNodeProjection(
        nodes,
        edges,
        brightnessAttribute,
        materialSourceUrlById || {},
        expandedNodeIds
      ),
    [nodes, edges, brightnessAttribute, materialSourceUrlById, expandedNodeIds]
  );

  const containerRef = useRef<HTMLDivElement | null>(null);
  const visualNodesRef = useRef<VisualNode[]>([]);
  const edgeListRef = useRef<VisualEdge[]>([]);
  const transformRef = useRef<TransformState>({ scale: 1, offsetX: 0, offsetY: 0 });
  const fitPendingRef = useRef(true);
  const mountedRef = useRef(false);

  const callbacksRef = useRef({
    onSelectNode,
    onToggleExpand: handleToggleExpand,
    onOpenMaterialRead,
    onOpenNodeVideo,
  });

  callbacksRef.current = {
    onSelectNode,
    onToggleExpand: handleToggleExpand,
    onOpenMaterialRead,
    onOpenNodeVideo,
  };

  const highlightedSetRef = useRef<Set<string>>(new Set());
  highlightedSetRef.current = new Set(highlightedNodeIds || (selectedNodeId ? [selectedNodeId] : []));

  const glowReachRef = useRef(1);
  glowReachRef.current = Math.max(0.2, Math.min(5, glowReach));

  const glowLightnessRef = useRef(1);
  glowLightnessRef.current = Math.max(0.2, Math.min(5, glowLightness));

  const glowWhiteLiftCapRef = useRef(0.55);
  glowWhiteLiftCapRef.current = Math.max(0.1, Math.min(1.5, glowWhiteLiftCap));

  const glowAlphaCapRef = useRef(1);
  glowAlphaCapRef.current = Math.max(0.1, Math.min(2, glowAlphaCap));

  const glowEnabledRef = useRef(true);
  glowEnabledRef.current = glowEnabled;

  const nodeFillOpacityRef = useRef(1);
  nodeFillOpacityRef.current = Math.max(0.1, Math.min(1, nodeFillOpacity));

  useEffect(() => {
    const existing = new Map(visualNodesRef.current.map((node) => [node.id, node]));
    visualNodesRef.current = toVisualNodes(projection.nodes, existing);
    edgeListRef.current = projection.edges;
    fitPendingRef.current = !mountedRef.current;
    mountedRef.current = true;
  }, [projection]);

  useEffect(() => {
    fitPendingRef.current = true;
  }, [fitTrigger]);

  useEffect(() => {
    setHoverPreview(null);
  }, [selectedNodeId, nodes.length, edges.length]);

  useEffect(() => {
    const host = containerRef.current;
    if (!host) {
      return;
    }

    let dispose = false;
    let sketchInstance: { remove: () => void } | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const load = async () => {
      const p5Module = await import("p5");
      if (dispose) {
        return;
      }

      const P5 = p5Module.default;

      sketchInstance = new P5((p: any) => {
        const dragState = {
          mode: "none" as "none" | "pan" | "node",
          nodeId: "",
          panStartX: 0,
          panStartY: 0,
          startOffsetX: 0,
          startOffsetY: 0,
        };

        const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

        const screenToWorld = (screenX: number, screenY: number) => {
          const transform = transformRef.current;
          return {
            x: (screenX - transform.offsetX) / transform.scale,
            y: (screenY - transform.offsetY) / transform.scale,
          };
        };

        const getNodeAt = (screenX: number, screenY: number): VisualNode | null => {
          const point = screenToWorld(screenX, screenY);
          for (let index = visualNodesRef.current.length - 1; index >= 0; index -= 1) {
            const node = visualNodesRef.current[index];
            const dx = point.x - node.x;
            const dy = point.y - node.y;
            if (dx * dx + dy * dy <= node.radius * node.radius) {
              return node;
            }
          }
          return null;
        };

        const fitToView = () => {
          const graphNodes = visualNodesRef.current;
          if (graphNodes.length === 0 || p.width <= 0 || p.height <= 0) {
            return;
          }

          let minX = Infinity;
          let maxX = -Infinity;
          let minY = Infinity;
          let maxY = -Infinity;

          for (const node of graphNodes) {
            minX = Math.min(minX, node.x - node.radius);
            maxX = Math.max(maxX, node.x + node.radius);
            minY = Math.min(minY, node.y - node.radius);
            maxY = Math.max(maxY, node.y + node.radius);
          }

          const width = Math.max(maxX - minX, 1);
          const height = Math.max(maxY - minY, 1);
          const padding = 56;

          const scaleX = (p.width - padding * 2) / width;
          const scaleY = (p.height - padding * 2) / height;
          const nextScale = clamp(Math.min(scaleX, scaleY), 0.2, 3.5);

          const centerX = (minX + maxX) / 2;
          const centerY = (minY + maxY) / 2;

          transformRef.current.scale = nextScale;
          transformRef.current.offsetX = p.width / 2 - centerX * nextScale;
          transformRef.current.offsetY = p.height / 2 - centerY * nextScale;
        };

        let frameTick = 0;
        let lowMotionFrames = 0;
        let simulationPaused = false;

        const applyForces = (): number => {
          const graphNodes = visualNodesRef.current;
          const graphEdges = edgeListRef.current;

          if (graphNodes.length <= 1) {
            return 0;
          }

          const nodeById = new Map(graphNodes.map((node) => [node.id, node]));
          const repulsionStrength = 4400;
          const springStrength = 0.015;
          const springLength = 180;
          const damping = 0.9;
          const centerPull = 0.002;

          for (let i = 0; i < graphNodes.length; i += 1) {
            const a = graphNodes[i];
            for (let j = i + 1; j < graphNodes.length; j += 1) {
              const b = graphNodes[j];
              let dx = a.x - b.x;
              let dy = a.y - b.y;
              let distSq = dx * dx + dy * dy;
              if (distSq < 0.01) {
                dx = (Math.random() - 0.5) * 0.01;
                dy = (Math.random() - 0.5) * 0.01;
                distSq = dx * dx + dy * dy;
              }
              const distance = Math.sqrt(distSq);
              const force = repulsionStrength / distSq;
              const fx = (dx / distance) * force;
              const fy = (dy / distance) * force;

              if (!(dragState.mode === "node" && dragState.nodeId === a.id)) {
                a.vx += fx;
                a.vy += fy;
              }
              if (!(dragState.mode === "node" && dragState.nodeId === b.id)) {
                b.vx -= fx;
                b.vy -= fy;
              }
            }
          }

          for (const edge of graphEdges) {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) {
              continue;
            }

            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 0.0001);
            const extension = distance - springLength;
            const force = extension * springStrength;
            const fx = (dx / distance) * force;
            const fy = (dy / distance) * force;

            if (!(dragState.mode === "node" && dragState.nodeId === source.id)) {
              source.vx += fx;
              source.vy += fy;
            }
            if (!(dragState.mode === "node" && dragState.nodeId === target.id)) {
              target.vx -= fx;
              target.vy -= fy;
            }
          }

          let totalMotion = 0;
          for (const node of graphNodes) {
            if (dragState.mode === "node" && dragState.nodeId === node.id) {
              node.vx = 0;
              node.vy = 0;
              continue;
            }

            node.vx += (0 - node.x) * centerPull;
            node.vy += (0 - node.y) * centerPull;
            node.vx *= damping;
            node.vy *= damping;
            node.x += node.vx;
            node.y += node.vy;
            totalMotion += Math.abs(node.vx) + Math.abs(node.vy);
          }

          return totalMotion / graphNodes.length;
        };

        p.setup = () => {
          const width = Math.max(host.clientWidth, 300);
          const height = Math.max(host.clientHeight, 240);
          p.createCanvas(width, height);
          p.textFont("Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif");
          p.smooth();
          fitPendingRef.current = true;
        };

        p.draw = () => {
          p.clear();
          p.background(0, 0, 0, 255);

          if (fitPendingRef.current) {
            fitToView();
            fitPendingRef.current = false;
            simulationPaused = false;
            lowMotionFrames = 0;
          }

          frameTick += 1;
          const isInteracting = dragState.mode !== "none" || p.mouseIsPressed;
          if (isInteracting) {
            simulationPaused = false;
            lowMotionFrames = 0;
          }

          const shouldRunPhysics = isInteracting || !simulationPaused;
          if (shouldRunPhysics && (isInteracting || frameTick % 2 === 0)) {
            const avgMotion = applyForces();
            if (!isInteracting) {
              if (avgMotion < 0.35) {
                lowMotionFrames += 1;
              } else {
                lowMotionFrames = 0;
              }
              if (lowMotionFrames > 60) {
                simulationPaused = true;
              }
            }
          }

          const transform = transformRef.current;
          p.push();
          p.translate(transform.offsetX, transform.offsetY);
          p.scale(transform.scale);

          const renderNodes = visualNodesRef.current;
          const nodeById = new Map(renderNodes.map((node) => [node.id, node]));

          p.strokeWeight(1.2 / Math.max(transform.scale, 0.001));
          for (const edge of edgeListRef.current) {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) {
              continue;
            }

            const isMaterialEdge = edge.edgeType.toUpperCase().includes("MATERIAL");
            p.stroke(isMaterialEdge ? 98 : 124, isMaterialEdge ? 121 : 143, isMaterialEdge ? 147 : 168, 180);
            p.line(source.x, source.y, target.x, target.y);
          }

          const canvasContext = p.drawingContext as CanvasRenderingContext2D;
          const previousComposite = canvasContext.globalCompositeOperation;
          const glowEnabledControl = glowEnabledRef.current;
          if (glowEnabledControl) {
            canvasContext.globalCompositeOperation = "screen";
          }

          const nodeCount = renderNodes.length;
          const effectiveBlurCap = nodeCount > 120 ? 14 : nodeCount > 80 ? 20 : 28;
          const showLabels = !isInteracting && transform.scale > 0.5;

          for (const node of renderNodes) {
            const selected = highlightedSetRef.current.has(node.id);
            const [r, g, b] = pkrColor(node.brightnessValue);
            const fillOpacityControl = nodeFillOpacityRef.current;

            if (node.type === "material") {
              p.fill(96, 80, 140, Math.round(190 * fillOpacityControl));
            } else if (node.type === "chapter") {
              p.fill(74, 109, 155, Math.round(190 * fillOpacityControl));
            } else {
              p.fill(r, g, b, Math.round(185 * fillOpacityControl));
            }

            if (glowEnabledControl) {
              const glowReachControl = glowReachRef.current;
              const glowLightnessControl = glowLightnessRef.current;
              const whiteLiftCapControl = glowWhiteLiftCapRef.current;
              const alphaCapControl = glowAlphaCapRef.current;

              const baseGlowStrength = node.type === "topic"
                ? 0.15 + node.brightnessValue * 0.85
                : 0.22;
              const glowStrength = (selected
                ? Math.min(1, baseGlowStrength + 0.2)
                : baseGlowStrength);

              const reachStrength = glowStrength * glowReachControl;
              const blurAmount = (10 + reachStrength * 30) / Math.max(transform.scale, 0.001);
              const effectiveBlurAmount = Math.min(blurAmount, effectiveBlurCap);

              const energyBase = Math.min(1, Math.pow(glowStrength, 1.05));
              const energy = Math.min(1, Math.pow(energyBase * glowLightnessControl, 1.08));
              const liftToWhite = Math.min(1, 0.06 + energy * whiteLiftCapControl);
              const glowR = Math.round(r + (255 - r) * liftToWhite);
              const glowG = Math.round(g + (255 - g) * liftToWhite);
              const glowB = Math.round(b + (255 - b) * liftToWhite);
              const glowAlpha = Math.min(1.5, 0.18 + energy * alphaCapControl);

              canvasContext.shadowBlur = effectiveBlurAmount;
              canvasContext.shadowColor = `rgba(${glowR}, ${glowG}, ${glowB}, ${glowAlpha})`;
            }
            p.stroke(selected ? 255 : 20, selected ? 255 : 28, selected ? 255 : 38, selected ? 255 : 190);
            p.strokeWeight((selected ? 3 : 1.5) / Math.max(transform.scale, 0.001));
            p.circle(node.x, node.y, node.radius * 2);
            canvasContext.shadowBlur = 0;
            canvasContext.shadowColor = "rgba(0,0,0,0)";

            if (node.hasChildren) {
              const indicatorRadius = Math.max(4, node.radius * 0.2);
              p.noStroke();
              p.fill(node.isExpanded ? 120 : 240, node.isExpanded ? 220 : 190, 120, 230);
              p.circle(node.x + node.radius * 0.62, node.y - node.radius * 0.62, indicatorRadius * 2);
            }

            if (showLabels) {
              p.noStroke();
              p.fill(233, 237, 244, 245);
              p.textAlign(p.CENTER, p.CENTER);
              p.textSize(Math.max(10, 12 / Math.max(transform.scale * 0.9, 0.7)));
              p.text(normalizeLabel(node.label), node.x, node.y - node.radius - 10 / Math.max(transform.scale, 0.001));
            }
          }

          canvasContext.globalCompositeOperation = previousComposite;
          canvasContext.shadowBlur = 0;
          canvasContext.shadowColor = "rgba(0,0,0,0)";

          p.pop();
        };

        p.mousePressed = () => {
          if (p.mouseX < 0 || p.mouseX > p.width || p.mouseY < 0 || p.mouseY > p.height) {
            return;
          }

          const hit = getNodeAt(p.mouseX, p.mouseY);
          if (hit) {
            setHoverPreview(null);
            dragState.mode = "node";
            dragState.nodeId = hit.id;
            callbacksRef.current.onSelectNode(hit.id);
            if (hit.hasChildren) {
              callbacksRef.current.onToggleExpand(hit.id);
            }
            return;
          }

          dragState.mode = "pan";
          dragState.panStartX = p.mouseX;
          dragState.panStartY = p.mouseY;
          dragState.startOffsetX = transformRef.current.offsetX;
          dragState.startOffsetY = transformRef.current.offsetY;
        };

        p.mouseDragged = () => {
          if (dragState.mode === "pan") {
            setHoverPreview(null);
            transformRef.current.offsetX = dragState.startOffsetX + (p.mouseX - dragState.panStartX);
            transformRef.current.offsetY = dragState.startOffsetY + (p.mouseY - dragState.panStartY);
            return;
          }

          if (dragState.mode === "node") {
            setHoverPreview(null);
            const point = screenToWorld(p.mouseX, p.mouseY);
            const node = visualNodesRef.current.find((entry) => entry.id === dragState.nodeId);
            if (!node) {
              return;
            }
            node.x = point.x;
            node.y = point.y;
            node.vx = 0;
            node.vy = 0;
            simulationPaused = false;
            lowMotionFrames = 0;
          }
        };

        p.mouseReleased = () => {
          dragState.mode = "none";
          dragState.nodeId = "";
        };

        p.mouseMoved = () => {
          if (dragState.mode !== "none") {
            return;
          }

          if (p.mouseX < 0 || p.mouseX > p.width || p.mouseY < 0 || p.mouseY > p.height) {
            setHoverPreview(null);
            return;
          }

          const hit = getNodeAt(p.mouseX, p.mouseY);
          if (!hit || !hit.youtubeThumbnailUrl) {
            setHoverPreview(null);
            return;
          }

          const thumbnailUrl = hit.youtubeThumbnailUrl;

          setHoverPreview((current) => {
            if (
              current &&
              current.nodeId === hit.id &&
              Math.abs(current.x - p.mouseX) < 2 &&
              Math.abs(current.y - p.mouseY) < 2
            ) {
              return current;
            }
            return {
              nodeId: hit.id,
              x: p.mouseX,
              y: p.mouseY,
              title: hit.label,
              thumbnailUrl,
            };
          });
        };

        p.mouseOut = () => {
          setHoverPreview(null);
        };

        p.doubleClicked = () => {
          const hit = getNodeAt(p.mouseX, p.mouseY);
          if (!hit) {
            return;
          }

          if (hit.youtubeEmbedUrl && callbacksRef.current.onOpenNodeVideo) {
            callbacksRef.current.onOpenNodeVideo({
              nodeId: hit.id,
              nodeTitle: hit.label,
              embedUrl: hit.youtubeEmbedUrl,
            });
            return;
          }

          if (hit.materialId && callbacksRef.current.onOpenMaterialRead) {
            callbacksRef.current.onOpenMaterialRead({
              materialId: hit.materialId,
              nodeId: hit.id,
              nodeTitle: hit.label,
            });
          }
        };

        p.mouseWheel = (event: WheelEvent) => {
          const zoomFactor = event.deltaY > 0 ? 0.93 : 1.08;
          const currentScale = transformRef.current.scale;
          const nextScale = clamp(currentScale * zoomFactor, 0.2, 4.2);

          const worldBefore = screenToWorld(p.mouseX, p.mouseY);
          transformRef.current.scale = nextScale;
          transformRef.current.offsetX = p.mouseX - worldBefore.x * nextScale;
          transformRef.current.offsetY = p.mouseY - worldBefore.y * nextScale;
          simulationPaused = false;
          lowMotionFrames = 0;

          return false;
        };

        p.windowResized = () => {
          const width = Math.max(host.clientWidth, 300);
          const height = Math.max(host.clientHeight, 240);
          p.resizeCanvas(width, height);
          fitPendingRef.current = true;
        };
      }, host);

      resizeObserver = new ResizeObserver(() => {
        fitPendingRef.current = true;
      });
      resizeObserver.observe(host);
    };

    void load();

    return () => {
      dispose = true;
      resizeObserver?.disconnect();
      sketchInstance?.remove();
    };
  }, []);

  return (
    <div className="h-full w-full rounded-lg border border-border-default bg-bg-base overflow-hidden relative">
      <div ref={containerRef} className="h-full w-full" />
      {hoverPreview && (
        <div
          className="pointer-events-none absolute z-20 w-56 overflow-hidden rounded-xl border border-border-default bg-bg-surface shadow-xl"
          style={{ left: hoverPreview.x + 14, top: hoverPreview.y + 14 }}
        >
          <img
            src={hoverPreview.thumbnailUrl}
            alt={`${hoverPreview.title} preview`}
            className="h-28 w-full object-cover"
            loading="lazy"
          />
          <div className="px-2 py-1 text-xs font-body text-text-primary truncate">{hoverPreview.title}</div>
        </div>
      )}
    </div>
  );
}
