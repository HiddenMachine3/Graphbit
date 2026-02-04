'use client';

import { useEffect, useMemo } from "react";
import ReactFlow, {
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Node,
  type Edge,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import type { GraphEdgeDTO, GraphNodeDTO } from "../../lib/types";
import GraphNode from "./GraphNode";
import GraphEdge from "./GraphEdge";
import useForceLayout from "../../lib/graph/useForceLayout";

export type KnowledgeGraphViewProps = {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
  selectedNodeId?: string | null;
  onSelectNode: (nodeId: string) => void;
  highlightedNodeIds?: string[];
  brightnessAttribute?: keyof GraphNodeDTO;
};

const nodeTypes = { graphNode: GraphNode };
const edgeTypes = { graphEdge: GraphEdge };

function buildFlowNodes(nodes: GraphNodeDTO[], brightnessAttribute: keyof GraphNodeDTO): Node[] {
  return nodes.map((node, index) => ({
    id: node.id,
    type: "graphNode",
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
  }));
}

export default function KnowledgeGraphView({
  nodes,
  edges,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
  brightnessAttribute = 'proven_knowledge_rating',
}: KnowledgeGraphViewProps) {
  const baseNodes = useMemo(() => buildFlowNodes(nodes, brightnessAttribute), [nodes, brightnessAttribute]);
  const baseEdges = useMemo(() => buildFlowEdges(edges), [edges]);
  const [flowNodes, setFlowNodes, onFlowNodesChange] = useNodesState(baseNodes);
  const [flowEdges, setFlowEdges, onFlowEdgesChange] = useEdgesState(baseEdges);

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

  useForceLayout(baseNodes, baseEdges, setFlowNodes);

  return (
    <div className="h-[520px] w-full rounded border border-slate-200 bg-white">
      <ReactFlowProvider>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onFlowNodesChange}
          onEdgesChange={onFlowEdgesChange}
          onNodeClick={(_, node) => onSelectNode(node.id)}
          fitView
        >
          <MiniMap />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
