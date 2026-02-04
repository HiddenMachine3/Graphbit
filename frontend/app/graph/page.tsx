"use client";

import { useEffect, useState } from "react";

import { fetchGraphSummary } from "../../lib/api/graph";
import type { GraphSummaryDTO, GraphNodeDTO } from "../../lib/types";
import Loading from "../../components/Loading";
import ErrorState from "../../components/ErrorState";
import KnowledgeGraphView from "../../components/graph/KnowledgeGraphView";
import NodeDetailPanel from "../../components/graph/NodeDetailPanel";
import GraphLegend from "../../components/graph/GraphLegend";

export default function GraphPage() {
  const [summary, setSummary] = useState<GraphSummaryDTO | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchGraphSummary()
      .then((data) => {
        if (mounted) {
          setSummary(data);
          setSelectedNodeId(data.nodes[0]?.id ?? null);
        }
      })
      .catch((err) => {
        if (mounted) {
          const message = err instanceof Error ? err.message : "Failed to load graph";
          setError(message);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const selectedNode: GraphNodeDTO | null =
    summary?.nodes.find((node) => node.id === selectedNodeId) ?? null;

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!summary) {
    return (
      <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-500">
        No graph data available.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
        <p className="text-sm text-slate-500">Visualized from backend graph data</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <KnowledgeGraphView
          nodes={summary.nodes}
          edges={summary.edges}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
        <div className="flex flex-col gap-4">
          <NodeDetailPanel node={selectedNode} />
          <GraphLegend />
        </div>
      </div>
    </section>
  );
}
