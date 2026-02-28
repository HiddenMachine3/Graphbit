import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type MaterialNodeProps = {
  data: GraphNodeDTO & { brightnessAttribute?: keyof GraphNodeDTO };
  selected: boolean;
};

export default function MaterialNode({ data, selected }: MaterialNodeProps) {
  return (
    <div
      title={`Material: ${data.topic_name}`}
      className={`flex h-14 w-14 flex-col items-center justify-center rounded-2xl border text-center text-xs shadow-sm transition ${
        selected ? "ring-2 ring-border-accent" : ""
      }`}
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        borderColor: "rgba(255, 255, 255, 0.15)",
      }}
    >
      <div className="px-1 text-xs font-semibold font-heading text-white">Material</div>
      <div className="mt-0.5 line-clamp-2 px-1 text-xs font-normal font-body text-text-secondary">
        {data.topic_name}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        style={{ left: "50%", top: "50%", transform: "translate(-50%, -50%)", opacity: 0 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ left: "50%", top: "50%", transform: "translate(-50%, -50%)", opacity: 0 }}
      />
    </div>
  );
}
