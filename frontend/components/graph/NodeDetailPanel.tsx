import type { GraphNodeDTO } from "../../lib/types";
import { getPKRTextClass } from "../../lib/colors";

type NodeDetailPanelProps = {
  node: GraphNodeDTO | null;
  onEdit?: () => void;
};

export default function NodeDetailPanel({ node, onEdit }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="rounded-2xl border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        Select a node to see details.
      </div>
    );
  }

  const pkr = node.proven_knowledge_rating;
  const forgetting = node.forgetting_score;
  const forgettingClass = forgetting > 0.6 ? 'text-pkr-low' : forgetting > 0.3 ? 'text-pkr-medium' : 'text-text-secondary';

  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="flex items-start justify-between">
        <div className="text-base font-semibold font-heading text-text-primary">{node.topic_name}</div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-xs font-medium font-body text-text-muted hover:text-text-secondary"
            title="Edit node properties"
          >
            ✎
          </button>
        )}
      </div>
      <div className="mt-2 space-y-1">
        <div>PKR: <span className={getPKRTextClass(pkr)}>{pkr.toFixed(2)}</span></div>
        <div>Forgetting: <span className={forgettingClass}>{forgetting.toFixed(2)}</span></div>
        <div>Linked questions: {node.linked_questions_count}</div>
        <div>Linked materials: {node.linked_materials_count}</div>
      </div>
    </div>
  );
}
