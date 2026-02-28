import type { WhyThisQuestionDTO } from "../../lib/types";
import ExplainTooltip from "./ExplainTooltip";

type WhyThisQuestionProps = {
  explanation: WhyThisQuestionDTO | null;
  isLoading?: boolean;
};

export default function WhyThisQuestion({ explanation, isLoading = false }: WhyThisQuestionProps) {
  if (isLoading) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        Loading explanation...
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-muted">
        No explanation available yet.
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-bg-surface p-4 text-sm font-body text-text-secondary">
      <div className="text-sm font-semibold font-heading text-text-primary">Why this question</div>
      <div className="mt-3 space-y-2">
        <div>
          <span className="label-caps text-text-muted">Focus areas</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {explanation.target_nodes.map((node) => (
              <span
                key={node}
                className="rounded-full border border-border-default bg-bg-elevated px-2 py-0.5 text-xs text-text-secondary"
              >
                {node}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span>Weakness level</span>
          <span className="text-sm font-medium capitalize text-text-primary">
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
