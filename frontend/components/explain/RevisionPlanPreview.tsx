import type { RevisionPlanItemDTO } from "../../lib/types";
import ExplainTooltip from "./ExplainTooltip";

type RevisionPlanPreviewProps = {
  items: RevisionPlanItemDTO[];
  isLoading?: boolean;
};

export default function RevisionPlanPreview({ items, isLoading = false }: RevisionPlanPreviewProps) {
  if (isLoading) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        Loading revision plan...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        No revision plan available.
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="text-sm font-semibold font-heading text-text-primary">Revision plan preview</div>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div
            key={item.node_id}
            className="flex flex-col gap-1 rounded border border-border-default bg-bg-elevated px-3 py-2"
          >
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-text-primary">{item.topic}</div>
              <span className="rounded-full bg-bg-hover px-2 py-0.5 text-xs font-medium text-text-secondary">
                {item.timing}
              </span>
            </div>
            <ExplainTooltip label="Reason" text={item.reason} />
          </div>
        ))}
      </div>
    </div>
  );
}
