import { useEffect } from "react";
import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceX,
  forceY,
  forceRadial,
  forceSimulation,
  type SimulationNodeDatum,
} from "d3-force";
import type { Edge, Node } from "reactflow";

const MIN_RADIUS = 60;
const MAX_RADIUS = 280;

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(input: string) {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createSeed(nodes: Node[], edges: Edge[]) {
  const nodeKey = nodes.map((node) => node.id).sort().join("|");
  const edgeKey = edges
    .map((edge) => `${edge.source}->${edge.target}`)
    .sort()
    .join("|");
  return hashString(`${nodeKey}::${edgeKey}`) || 1;
}

export default function useForceLayout(nodes: Node[], edges: Edge[], setNodes: (payload: Node[] | ((nodes: Node[]) => Node[])) => void) {
  useEffect(() => {
    if (nodes.length === 0) {
      return undefined;
    }

    const simulationNodes = nodes.map((node) => ({
      ...node,
      x: node.position.x,
      y: node.position.y,
    }));

    const linkForce = forceLink(simulationNodes)
      .id((d: SimulationNodeDatum) => (d as Node).id)
      .links(edges.map((edge) => ({ ...edge })))
      .distance(120)
      .strength(0.8);

    const chargeForce = forceManyBody().strength((d: SimulationNodeDatum) => {
      const node = d as Node;
      const importance = clamp((node.data as { importance?: number })?.importance ?? 0.5);
      return importance > 0.7 ? -600 : -260;
    });

    const centerForce = forceCenter(0, 0);
    const centerPullX = forceX(0).strength(0.08);
    const centerPullY = forceY(0).strength(0.08);

    const radialForce = forceRadial((d: SimulationNodeDatum) => {
      const node = d as Node;
      const importance = clamp((node.data as { importance?: number })?.importance ?? 0.5);
      return MAX_RADIUS - (MAX_RADIUS - MIN_RADIUS) * importance;
    }, 0, 0).strength(0.05);

    const seed = createSeed(nodes, edges);

    const simulation = forceSimulation(simulationNodes)
      .force("link", linkForce)
      .force("charge", chargeForce)
      .force("center", centerForce)
      .force("centerX", centerPullX)
      .force("centerY", centerPullY)
      .force("radial", radialForce)
      .alpha(1)
      .alphaDecay(0.04)
      .randomSource(mulberry32(seed));

    simulation.on("tick", () => {
      setNodes((current) =>
        current.map((node) => {
          const simNode = simulationNodes.find((item) => item.id === node.id);
          if (!simNode) {
            return node;
          }
          return {
            ...node,
            position: {
              x: simNode.x ?? 0,
              y: simNode.y ?? 0,
            },
          };
        })
      );
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, setNodes]);
}
