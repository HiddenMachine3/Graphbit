import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type GraphNodeProps = {
  data: GraphNodeDTO;
  selected: boolean;
};

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

export default function GraphNode({ data, selected }: GraphNodeProps) {
  const brightness = clamp(data.proven_knowledge_rating);
  const borderIntensity = clamp(data.forgetting_score);
  const importance = clamp(data.importance);

  const minSize = 48;
  const maxSize = 110;
  const size = minSize + (maxSize - minSize) * importance;

  const backgroundColor = `rgba(59, 130, 246, ${0.15 + brightness * 0.65})`;
  const borderColor = `rgba(239, 68, 68, ${0.2 + borderIntensity * 0.75})`;

  return (
    <div
      title={`PKR: ${data.proven_knowledge_rating.toFixed(2)} | Importance: ${data.importance.toFixed(
        2
      )} | Forgetting: ${data.forgetting_score.toFixed(2)}`}
      className={`flex flex-col items-center justify-center rounded-full border-2 text-center text-[11px] shadow-sm transition ${
        selected ? "ring-2 ring-slate-900" : ""
      }`}
      style={{ backgroundColor, borderColor, width: size, height: size }}
    >
      <div className="px-2 font-semibold text-slate-900">{data.topic_name}</div>
      <div className="mt-1 text-[10px] text-slate-700">PKR {data.proven_knowledge_rating.toFixed(2)}</div>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}
