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
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Loading weakness details...
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No weakness details available.
      </div>
    );
  }

  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-700">
      <div className="text-sm font-semibold text-slate-800">Weakness breakdown</div>
      <div className="mt-3 space-y-2">
        {nodes.map((node) => (
          <div
            key={node.node_id}
            className="flex items-center justify-between rounded border border-slate-100 bg-slate-50 px-3 py-2"
          >
            <div>
              <div className="text-sm font-medium text-slate-900">{node.topic}</div>
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
