import type { GraphNodeDTO } from "../../lib/types";

type NodeDetailPanelProps = {
  node: GraphNodeDTO | null;
  onEdit?: () => void;
};

export default function NodeDetailPanel({ node, onEdit }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Select a node to see details.
      </div>
    );
  }

  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-700">
      <div className="flex items-start justify-between">
        <div className="text-base font-semibold text-slate-900">{node.topic_name}</div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-xs font-medium text-blue-600 hover:text-blue-700"
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
