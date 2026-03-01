import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import type { Edge, Node } from "reactflow";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type LayoutNode = SimulationNodeDatum & {
  id: string;
  type?: string;
  data: Node["data"];
  x: number;
  y: number;
};

type LayoutLink = SimulationLinkDatum<LayoutNode> & {
  source: string | LayoutNode;
  target: string | LayoutNode;
};

export type ForceLayoutHandlers = {
  onNodeDrag: (nodeId: string, x: number, y: number) => void;
  onNodeDragEnd: (nodeId: string) => void;
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function buildAdjacency(edges: Edge[]) {
  const adj = new Map<string, Set<string>>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, new Set());
    if (!adj.has(e.target)) adj.set(e.target, new Set());
    adj.get(e.source)!.add(e.target);
    adj.get(e.target)!.add(e.source);
  }
  return adj;
}

function pickRootNode(nodes: Node[], edges: Edge[]) {
  if (nodes.length === 0) return null;
  const deg = new Map<string, number>();
  for (const e of edges) {
    deg.set(e.source, (deg.get(e.source) ?? 0) + 1);
    deg.set(e.target, (deg.get(e.target) ?? 0) + 1);
  }
  let best: Node | null = null;
  let bestScore = -1;
  for (const n of nodes) {
    const imp = (n.data as { importance?: number } | undefined)?.importance ?? 0.5;
    const score = (deg.get(n.id) ?? 0) * 2 + imp * 5;
    if (score > bestScore) {
      bestScore = score;
      best = n;
    }
  }
  return best;
}

/**
 * BFS from root to assign hop levels, then place nodes
 * in concentric rings for a clean initial layout.
 */
function computeInitialPositions(nodes: Node[], edges: Edge[]) {
  const positions = new Map<string, { x: number; y: number }>();
  const root = pickRootNode(nodes, edges);
  if (!root) return positions;

  const adj = buildAdjacency(edges);
  const hopMap = new Map<string, number>();
  const queue = [root.id];
  hopMap.set(root.id, 0);

  while (queue.length > 0) {
    const current = queue.shift()!;
    const hop = hopMap.get(current)!;
    for (const nbr of adj.get(current) ?? []) {
      if (!hopMap.has(nbr)) {
        hopMap.set(nbr, hop + 1);
        queue.push(nbr);
      }
    }
  }

  for (const n of nodes) {
    if (!hopMap.has(n.id)) hopMap.set(n.id, 3);
  }

  const levels = new Map<number, Node[]>();
  let maxHop = 0;
  for (const n of nodes) {
    const h = hopMap.get(n.id)!;
    maxHop = Math.max(maxHop, h);
    if (!levels.has(h)) levels.set(h, []);
    levels.get(h)!.push(n);
  }

  positions.set(root.id, { x: 0, y: 0 });

  const ringSpacing = 280;
  for (let h = 1; h <= maxHop; h++) {
    const lvl = (levels.get(h) ?? []).filter((n) => n.id !== root.id);
    if (lvl.length === 0) continue;
    const radius = ringSpacing * h;
    const step = (2 * Math.PI) / lvl.length;
    lvl.forEach((n, i) => {
      const angle = -Math.PI / 2 + i * step;
      positions.set(n.id, {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      });
    });
  }

  return positions;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

export default function useForceLayout(
  nodes: Node[],
  edges: Edge[],
  setNodes: (payload: Node[] | ((nodes: Node[]) => Node[])) => void,
  postProcess?: (nodes: Node[]) => Node[]
): ForceLayoutHandlers {
  /* Keep latest setter in a ref so the tick callback never goes stale */
  const setNodesRef = useRef(setNodes);
  setNodesRef.current = setNodes;
  const postProcessRef = useRef(postProcess);
  postProcessRef.current = postProcess;

  /* Simulation + its internal node array survive across renders */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const simRef = useRef<any>(null);
  const simNodesRef = useRef<LayoutNode[]>([]);

  /**
   * Stable structural key – only changes when the set of node-ids
   * or edge-pairs changes, NOT on every position update.
   */
  const graphKey = useMemo(() => {
    const nk = nodes
      .map((n) => n.id)
      .sort()
      .join(",");
    const ek = edges
      .map((e) => `${e.source}-${e.target}`)
      .sort()
      .join(",");
    return `${nk}||${ek}`;
  }, [nodes, edges]);

  /* ---- create / destroy simulation ---- */
  useEffect(() => {
    if (nodes.length === 0) {
      simRef.current = null;
      simNodesRef.current = [];
      return undefined;
    }

    const initPos = computeInitialPositions(nodes, edges);

    const materialNodesList = nodes.filter(n => n.type === "materialNode").sort((a, b) => a.id.localeCompare(b.id));

    const simulationNodes: LayoutNode[] = nodes.map((node) => {
      /* Reuse existing position when available (non-zero) */
      const hasPos = node.position.x !== 0 || node.position.y !== 0;
      const fallback = initPos.get(node.id);

      const isChapter = node.data?.node_type === "chapter";
      const isMaterial = node.type === "materialNode";
      const seq = node.data?.sequence_number ?? 1;

      let initialX = hasPos ? node.position.x : (fallback?.x ?? (Math.random() - 0.5) * 200);
      let initialY = hasPos ? node.position.y : (fallback?.y ?? (Math.random() - 0.5) * 200);
      let fx: number | undefined | null = undefined;
      let fy: number | undefined | null = undefined;

      // Lock chapters on the horizontal timeline, distribute materials vertically
      if (isChapter) {
        const targetX = (seq - 1) * 800;
        initialX = targetX;
        initialY = 0;
        fx = targetX;
        fy = 0;
      } else if (isMaterial) {
        const matIdx = materialNodesList.findIndex(n => n.id === node.id);
        const targetX = -800;
        const targetY = (matIdx - (materialNodesList.length - 1) / 2) * 600;
        initialX = targetX;
        initialY = targetY;
        fx = targetX;
        fy = targetY;
      }

      return {
        ...node,
        x: initialX,
        y: initialY,
        fx,
        fy,
      };
    });

    const linkData: LayoutLink[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    /* ---------- forces (Vis-Network-like) ---------- */

    const linkForce = forceLink<LayoutNode, LayoutLink>(linkData)
      .id((d) => d.id)
      .distance(300)
      .strength(0.4);

    const chargeForce = forceManyBody<LayoutNode>()
      .strength(-800)
      .distanceMax(1200);

    const centerForce = forceCenter(0, 0).strength(0.04);

    /* Mild gravity so disconnected nodes don't fly away */
    const gravityX = forceX<LayoutNode>(0).strength(0.02);
    const gravityY = forceY<LayoutNode>(0).strength(0.02);

    /* Increase collision radius to prevent overlapping labels */
    const collideForce = forceCollide<LayoutNode>(150).strength(0.9);

    const simulation = forceSimulation(simulationNodes)
      .force("link", linkForce)
      .force("charge", chargeForce)
      .force("center", centerForce)
      .force("gravityX", gravityX)
      .force("gravityY", gravityY)
      .force("collide", collideForce)
      .alpha(1)
      .alphaDecay(0.012)
      .velocityDecay(0.35)
      .alphaTarget(0.015); /* persistent subtle jiggle */

    simRef.current = simulation;
    simNodesRef.current = simulationNodes;

    let tickCount = 0;
    simulation.on("tick", () => {
      tickCount += 1;
      if (tickCount % 3 !== 0) return; /* update every 3rd tick for perf */

      setNodesRef.current((current) =>
      (postProcessRef.current
        ? postProcessRef.current(
          current.map((node) => {
            const sim = simulationNodes.find((n) => n.id === node.id);
            if (!sim) return node;

            // Skip updating position for timeline anchors to prevent jitter
            if (node.data?.node_type === "chapter" || node.data?.node_type === "material") {
              return { ...node, position: { x: sim.x ?? 0, y: sim.y ?? 0 } };
            }

            /* Don't override nodes currently pinned (being dragged) */
            if (sim.fx != null && !(node.data?.node_type === "chapter" || node.data?.node_type === "material")) return node;

            return {
              ...node,
              position: { x: sim.x ?? 0, y: sim.y ?? 0 },
            };
          })
        )
        : current.map((node) => {
          const sim = simulationNodes.find((n) => n.id === node.id);
          if (!sim) return node;

          // Skip updating position for timeline anchors to prevent jitter
          if (node.data?.node_type === "chapter" || node.data?.node_type === "material") {
            return { ...node, position: { x: sim.x ?? 0, y: sim.y ?? 0 } };
          }

          /* Don't override nodes currently pinned (being dragged) */
          if (sim.fx != null && !(node.data?.node_type === "chapter" || node.data?.node_type === "material")) return node;

          return {
            ...node,
            position: { x: sim.x ?? 0, y: sim.y ?? 0 },
          };
        }))
      );
    });

    return () => {
      simulation.stop();
      simRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphKey]);

  /* ---- drag handlers (fx/fy pinning, standard D3 pattern) ---- */

  const onNodeDrag = useCallback((nodeId: string, x: number, y: number) => {
    const sim = simNodesRef.current.find((n) => n.id === nodeId);
    if (sim) {
      sim.fx = x;
      sim.fy = y;
    }
    /* Re-heat so connected nodes follow the drag */
    const s = simRef.current;
    if (s && s.alpha() < 0.15) {
      s.alpha(0.15).restart();
    }
  }, []);

  const onNodeDragEnd = useCallback((nodeId: string) => {
    const sim = simNodesRef.current.find((n) => n.id === nodeId);
    if (sim) {
      // Don't unpin chapters/materials on drag end
      const isAnchor = sim.data?.node_type === "chapter" || sim.data?.node_type === "material";
      if (!isAnchor) {
        sim.fx = null;
        sim.fy = null;
      }
    }
  }, []);

  return { onNodeDrag, onNodeDragEnd };
}
