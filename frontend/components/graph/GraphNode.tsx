import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type GraphNodeProps = {
  data: GraphNodeDTO & { brightnessAttribute?: keyof GraphNodeDTO };
  selected: boolean;
};

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function normalizeValue(value: any, attribute: keyof GraphNodeDTO): number {
  // Some attributes like view_frequency can be large integers, so we normalize them
  if (attribute === 'view_frequency') {
    // Assuming max view frequency is around 100
    return clamp(Math.min(value / 100, 1));
  }
  return clamp(value);
}

export default function GraphNode({ data, selected }: GraphNodeProps) {
  const brightnessAttribute = data.brightnessAttribute || 'proven_knowledge_rating';
  const brightnessValue = toNumber(data[brightnessAttribute], 0);
  const brightness = normalizeValue(brightnessValue, brightnessAttribute);
  const borderIntensity = clamp(data.forgetting_score);
  const importance = clamp(data.importance);

  const minSize = 48;
  const maxSize = 110;
  const size = minSize + (maxSize - minSize) * importance;

  const boostedBrightness = clamp(brightness * 1.6);
  const backgroundColor = `rgba(178, 38, 76, ${0.1 + boostedBrightness * 0.85})`;
  const borderColor = `rgba(120, 24, 46, ${0.2 + borderIntensity * 0.7})`;
  const glowStrength = 8 + boostedBrightness * 28;
  const glowOpacity = 0.15 + boostedBrightness * 0.45;
  const glowColor = `rgba(178, 38, 76, ${glowOpacity})`;

  return (
    <div
      title={`${brightnessAttribute.replace(/_/g, ' ')}: ${brightnessValue.toFixed(2)} | Importance: ${data.importance.toFixed(
        2
      )} | Forgetting: ${data.forgetting_score.toFixed(2)}`}
      className={`flex flex-col items-center justify-center rounded-full border-2 text-center text-[11px] shadow-sm transition ${
        selected ? "ring-2 ring-slate-900" : ""
      }`}
      style={{
        backgroundColor,
        borderColor,
        width: size,
        height: size,
        boxShadow: `0 0 ${glowStrength}px ${glowColor}, 0 0 ${glowStrength * 1.8}px ${glowColor}`,
      }}
    >
      <div className="px-2 font-semibold text-white">{data.topic_name}</div>
      <div className="mt-1 text-[10px] text-slate-200/80">{brightnessAttribute.replace(/_/g, ' ')} {brightnessValue.toFixed(2)}</div>
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
