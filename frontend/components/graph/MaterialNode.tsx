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
      className={`flex h-14 w-14 flex-col items-center justify-center rounded-2xl border text-center text-[10px] shadow-sm transition ${
        selected ? "ring-2 ring-rose-200" : ""
      }`}
      style={{
        backgroundColor: "rgba(178, 38, 76, 0.2)",
        borderColor: "rgba(178, 38, 76, 0.55)",
      }}
    >
      <div className="px-1 text-[9px] font-semibold text-white">Material</div>
      <div className="mt-0.5 line-clamp-2 px-1 text-[9px] text-rose-100/90">
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
