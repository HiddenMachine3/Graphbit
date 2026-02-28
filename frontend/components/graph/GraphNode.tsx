import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";
import { getPKRRgba } from "../../lib/colors";

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

  const pkr = clamp(toNumber(data.proven_knowledge_rating, 0));
  const boostedBrightness = clamp(brightness * 1.6);
  const backgroundColor = getPKRRgba(pkr, 0.1 + boostedBrightness * 0.85);
  const borderColor = getPKRRgba(pkr, 0.2 + borderIntensity * 0.7);
  const glowStrength = 8 + boostedBrightness * 28;
  const glowOpacity = 0.15 + boostedBrightness * 0.45;
  const glowColor = getPKRRgba(pkr, glowOpacity);

  return (
    <div
      title={`${brightnessAttribute.replace(/_/g, ' ')}: ${brightnessValue.toFixed(2)} | Importance: ${data.importance.toFixed(
        2
      )} | Forgetting: ${data.forgetting_score.toFixed(2)}`}
      className={`flex flex-col items-center justify-center rounded-full border-2 text-center text-xs shadow-sm transition ${
        selected ? "ring-2 ring-border-accent" : ""
      }`}
      style={{
        backgroundColor,
        borderColor,
        width: size,
        height: size,
        boxShadow: `0 0 ${glowStrength}px ${glowColor}, 0 0 ${glowStrength * 1.8}px ${glowColor}`,
      }}
    >
      <div className="px-2 text-xs font-semibold font-heading text-white">{data.topic_name}</div>
      <div className="mt-1 text-xs font-normal font-body text-text-secondary">{brightnessAttribute.replace(/_/g, ' ')} {brightnessValue.toFixed(2)}</div>
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
