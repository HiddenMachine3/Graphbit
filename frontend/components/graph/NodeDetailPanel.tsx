import type { GraphNodeDTO } from "../../lib/types";

type NodeDetailPanelProps = {
  node: GraphNodeDTO | null;
  onEdit?: () => void;
};

export default function NodeDetailPanel({ node, onEdit }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
        Select a node to see details.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
      <div className="flex items-start justify-between">
        <div className="text-base font-semibold text-white">{node.topic_name}</div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-xs font-medium text-rose-300 hover:text-rose-200"
            title="Edit node properties"
          >
            ✎
          </button>
        )}
      </div>
      <div className="mt-2 space-y-1">
        <div>PKR: {node.proven_knowledge_rating.toFixed(2)}</div>
        <div>Forgetting: {node.forgetting_score.toFixed(2)}</div>
        <div>Linked questions: {node.linked_questions_count}</div>
        <div>Linked materials: {node.linked_materials_count}</div>
      </div>
    </div>
  );
}
