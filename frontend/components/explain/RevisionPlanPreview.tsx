import type { RevisionPlanItemDTO } from "../../lib/types";
import ExplainTooltip from "./ExplainTooltip";

type RevisionPlanPreviewProps = {
  items: RevisionPlanItemDTO[];
  isLoading?: boolean;
};

export default function RevisionPlanPreview({ items, isLoading = false }: RevisionPlanPreviewProps) {
  if (isLoading) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Loading revision plan...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No revision plan available.
      </div>
    );
  }

  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-700">
      <div className="text-sm font-semibold text-slate-800">Revision plan preview</div>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div
            key={item.node_id}
            className="flex flex-col gap-1 rounded border border-slate-100 bg-slate-50 px-3 py-2"
          >
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-900">{item.topic}</div>
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
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
