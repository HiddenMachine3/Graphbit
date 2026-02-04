import type { WhyThisQuestionDTO } from "../../lib/types";
import ExplainTooltip from "./ExplainTooltip";

type WhyThisQuestionProps = {
  explanation: WhyThisQuestionDTO | null;
  isLoading?: boolean;
};

export default function WhyThisQuestion({ explanation, isLoading = false }: WhyThisQuestionProps) {
  if (isLoading) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Loading explanation...
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No explanation available yet.
      </div>
    );
  }

  return (
    <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-700">
      <div className="text-sm font-semibold text-slate-800">Why this question</div>
      <div className="mt-3 space-y-2">
        <div>
          <span className="text-xs uppercase text-slate-400">Focus areas</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {explanation.target_nodes.map((node) => (
              <span
                key={node}
                className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600"
              >
                {node}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span>Weakness level</span>
          <span className="text-sm font-medium capitalize text-slate-900">
            {explanation.weakness_level}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Recency cue</span>
          <ExplainTooltip label="Why" text={explanation.forgetting_cue} />
        </div>
      </div>
    </div>
  );
}
