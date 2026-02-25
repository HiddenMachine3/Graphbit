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
  projectId: string | null;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  highlightedNodeIds?: string[];
  brightnessAttribute?: keyof GraphNodeDTO;
  onGraphUpdated?: () => void;
};

const nodeTypes = { graphNode: GraphNode, materialNode: MaterialNode };
const edgeTypes = { graphEdge: GraphEdge };

function buildFlowNodes(
  nodes: GraphNodeDTO[],
  brightnessAttribute: keyof GraphNodeDTO
): Node[] {
  return nodes.map((node) => ({
    id: node.id,
    type: node.node_type === "material" ? "materialNode" : "graphNode",
    position: { x: 0, y: 0 },
    data: { ...node, brightnessAttribute },
    selected: false,
  }));
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
  projectId,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
  brightnessAttribute = "proven_knowledge_rating",
  onGraphUpdated,
}: KnowledgeGraphViewProps) {
  const baseNodes = useMemo(
    () => buildFlowNodes(nodes, brightnessAttribute),
    [nodes, brightnessAttribute]
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

  const { onNodeDrag, onNodeDragEnd } = useForceLayout(
    layoutNodes,
    layoutEdges,
    setFlowNodes
  );

  const applyMaterialRepulsion = useCallback((current: Node[]) => {
    const repulsors = current.filter((node) => node.type === "materialNode");
    if (repulsors.length === 0) {
      return current;
    }

    const minDistance = 200;
    const minNodeDistance = 120;
    const minMaterialDistance = 160;

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
    <div className="h-full w-full rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
      <ReactFlowProvider>
        <GraphFlowCanvas
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onFlowEdgesChange}
          onConnect={onConnect}
          onSelectNode={onSelectNode}
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
};

function GraphFlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onSelectNode,
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

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, node) => onSelectNode(node.id)}
      fitView
    >
      <MiniMap />
      <Controls />
    </ReactFlow>
  );
}
