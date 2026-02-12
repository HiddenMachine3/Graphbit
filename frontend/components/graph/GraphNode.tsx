import { Handle, Position, type NodeProps } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type GraphNodeProps = NodeProps<GraphNodeDTO & { brightnessAttribute?: keyof GraphNodeDTO }>;

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function normalizeValue(value: any, attribute: keyof GraphNodeDTO): number {
  // Some attributes like view_frequency can be large integers, so we normalize them
  if (attribute === 'view_frequency') {
    // Assuming max view frequency is around 100
    return clamp(Math.min(value / 100, 1));
  }
  return clamp(value);
}

export default function GraphNode({ data, selected, isConnectable }: GraphNodeProps) {
  const brightnessAttribute = data.brightnessAttribute || 'proven_knowledge_rating';
  const brightnessValue = data[brightnessAttribute];
  const brightness = normalizeValue(brightnessValue, brightnessAttribute);
  const borderIntensity = clamp(data.forgetting_score);
  const importance = clamp(data.importance);
  const isChapterNode = data.id.startsWith("chapter_");

  const size = isChapterNode ? 14 : 18 + 18 * importance;

  const boostedBrightness = clamp(brightness * (isChapterNode ? 1.1 : 1.4));
  const baseColor = isChapterNode ? "217, 70, 239" : "148, 163, 184";
  const backgroundColor = `rgba(${baseColor}, ${isChapterNode ? 0.95 : 0.18 + boostedBrightness * 0.25})`;
  const borderColor = isChapterNode
    ? `rgba(${baseColor}, 1)`
    : `rgba(${baseColor}, ${0.2 + borderIntensity * 0.35})`;
  const glowStrength = isChapterNode ? 16 : 8 + boostedBrightness * 10;
  const glowOpacity = isChapterNode ? 0.55 : 0.12 + boostedBrightness * 0.18;
  const glowColor = `rgba(${baseColor}, ${glowOpacity})`;

  return (
    <div
      title={`${brightnessAttribute.replace(/_/g, ' ')}: ${brightnessValue.toFixed(2)} | Importance: ${data.importance.toFixed(
        2
      )} | Forgetting: ${data.forgetting_score.toFixed(2)}`}
      className={`relative flex flex-col items-center justify-center gap-1 text-center transition ${
        selected ? "ring-2 ring-slate-900" : ""
      }`}
    >
      <div
        className="rounded-full border"
        style={{
          backgroundColor,
          borderColor,
          width: size,
          height: size,
          boxShadow: `0 0 ${glowStrength}px ${glowColor}, 0 0 ${glowStrength * 1.4}px ${glowColor}`,
        }}
      />
      <div
        className={`max-w-[120px] truncate text-[11px] ${
          isChapterNode ? "text-fuchsia-200" : "text-slate-300"
        }`}
      >
        {data.topic_name}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={isConnectable}
        style={{
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          width: 26,
          height: 26,
          borderRadius: 999,
          background: "transparent",
          border: "none",
          opacity: 0,
          cursor: "crosshair",
          pointerEvents: "all",
          zIndex: 10,
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={isConnectable}
        style={{
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          width: 26,
          height: 26,
          borderRadius: 999,
          background: "transparent",
          border: "none",
          opacity: 0,
          cursor: "crosshair",
          pointerEvents: "all",
          zIndex: 10,
        }}
      />
    </div>
  );
}
