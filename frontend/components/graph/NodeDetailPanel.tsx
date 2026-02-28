import type { GraphNodeDTO } from "../../lib/types";
import { getPKRTextClass } from "../../lib/colors";

type NodeDetailPanelProps = {
  node: GraphNodeDTO | null;
  onEdit?: () => void;
  onDelete?: (nodeId: string) => void;
};

export default function NodeDetailPanel({ node, onEdit, onDelete }: NodeDetailPanelProps) {
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
  const canDelete = node.node_type !== "material" && !node.id.startsWith("material:");

  return (
    <div className="rounded-2xl border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="flex items-start justify-between">
        <div className="text-base font-semibold font-heading text-text-primary">{node.topic_name}</div>
        <div className="flex items-center gap-2">
          {canDelete && onDelete && (
            <button
              onClick={() => onDelete(node.id)}
              className="rounded border border-border-default bg-bg-elevated px-2 py-1 text-xs font-medium font-body text-text-muted hover:bg-bg-hover hover:text-text-secondary"
              title="Delete node"
              aria-label="Delete node"
              type="button"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 7h16" />
                <path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                <path d="M7 7l1 12a1 1 0 0 0 1 .9h6a1 1 0 0 0 1-.9l1-12" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
              </svg>
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="text-xs font-medium font-body text-text-muted hover:text-text-secondary"
              title="Edit node properties"
              type="button"
            >
              ✎
            </button>
          )}
        </div>
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
