import type { WeaknessNodeDTO } from "../../lib/types";
import ExplainTooltip from "./ExplainTooltip";

type WeaknessBreakdownProps = {
  nodes: WeaknessNodeDTO[];
  isLoading?: boolean;
};

const levelStyles: Record<WeaknessNodeDTO["weakness_level"], string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-rose-100 text-rose-700",
};

export default function WeaknessBreakdown({ nodes, isLoading = false }: WeaknessBreakdownProps) {
  if (isLoading) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        Loading weakness details...
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        No weakness details available.
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="text-sm font-semibold font-heading text-text-primary">Weakness breakdown</div>
      <div className="mt-3 space-y-2">
        {nodes.map((node) => (
          <div
            key={node.node_id}
            className="flex items-center justify-between rounded border border-border-default bg-bg-elevated px-3 py-2"
          >
            <div>
              <div className="text-sm font-medium text-text-primary">{node.topic}</div>
              <ExplainTooltip label="Why" text={node.explanation} />
            </div>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                levelStyles[node.weakness_level]
              }`}
            >
              {node.weakness_level}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
