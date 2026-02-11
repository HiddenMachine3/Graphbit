'use client';

import { useCallback, useEffect, useMemo, useRef } from "react";
import ReactFlow, {
  addEdge,
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type Node,
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
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  highlightedNodeIds?: string[];
  brightnessAttribute?: keyof GraphNodeDTO;
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
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
  brightnessAttribute = "proven_knowledge_rating",
}: KnowledgeGraphViewProps) {
  const baseNodes = useMemo(
    () => buildFlowNodes(nodes, brightnessAttribute),
    [nodes, brightnessAttribute]
  );
  const baseEdges = useMemo(() => buildFlowEdges(edges), [edges]);
  const layoutNodes = useMemo(
    () => baseNodes.filter((node) => node.type !== "materialNode"),
    [baseNodes]
  );
  const layoutEdges = useMemo(
    () =>
      baseEdges.filter(
        (edge) => (edge.data as { edgeType?: string } | undefined)?.edgeType !== "MATERIAL"
      ),
    [baseEdges]
  );
  const [flowNodes, setFlowNodes, onFlowNodesChange] = useNodesState(baseNodes);
  const [flowEdges, setFlowEdges, onFlowEdgesChange] = useEdgesState(baseEdges);
  const materialNodeIds = useMemo(
    () => new Set(nodes.filter((node) => node.node_type === "material").map((node) => node.id)),
    [nodes]
  );

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

  useForceLayout(layoutNodes, layoutEdges, setFlowNodes);

  useEffect(() => {
    if (materialNodeIds.size === 0) {
      return;
    }

    setFlowNodes((current) => {
      const nodeMap = new Map(current.map((node) => [node.id, node]));

      return current.map((node) => {
        if (!materialNodeIds.has(node.id)) {
          return node;
        }

        const connectedNodes = flowEdges
          .filter(
            (edge) =>
              edge.source === node.id &&
              (edge.data as { edgeType?: string } | undefined)?.edgeType === "MATERIAL"
          )
          .map((edge) => nodeMap.get(edge.target))
          .filter((target): target is Node => Boolean(target));

        if (connectedNodes.length === 0) {
          return node;
        }

        const averageX =
          connectedNodes.reduce((sum, target) => sum + (target.position?.x ?? 0), 0) /
          connectedNodes.length;
        const averageY =
          connectedNodes.reduce((sum, target) => sum + (target.position?.y ?? 0), 0) /
          connectedNodes.length;

        if (
          Math.abs((node.position?.x ?? 0) - averageX) < 1 &&
          Math.abs((node.position?.y ?? 0) - averageY) < 1
        ) {
          return node;
        }

        return {
          ...node,
          position: { x: averageX, y: averageY },
        };
      });
    });
  }, [flowEdges, materialNodeIds, setFlowNodes]);

  const onConnect = useCallback(
    async (connection: Connection) => {
      if (!connection.source || !connection.target) {
        return;
      }

      const edgePayload = {
        ...connection,
        type: "graphEdge",
      } as Edge;

      setFlowEdges((current) => addEdge(edgePayload, current));

      try {
        await createEdge(connection.source, connection.target, "APPLIED_WITH", 0.6);
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
    [setFlowEdges]
  );

  return (
    <div className="h-full w-full rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
      <ReactFlowProvider>
        <GraphFlowCanvas
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={onFlowNodesChange}
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
  onNodesChange: Parameters<typeof useNodesState>[2];
  onEdgesChange: Parameters<typeof useEdgesState>[2];
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
  }, [nodes, fitView]);

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
