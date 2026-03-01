import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";
import { getPKRRgba } from "../../lib/colors";

type GraphNodeProps = {
  data: GraphNodeDTO & {
    brightnessAttribute?: keyof GraphNodeDTO;
    youtubeThumbnailUrl?: string | null;
    youtubeEmbedUrl?: string | null;
    onOpenVideo?: () => void;
    isExpanded?: boolean;
    hasChildren?: boolean;
    onToggleExpand?: (nodeId: string) => void;
  };
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
  if (attribute === 'view_frequency') {
    return clamp(Math.min(value / 100, 1));
  }
  return clamp(value);
}

const CHAPTER_PALETTE = [
  { border: "#a78bfa", bg: "rgba(167,139,250,0.15)", glow: "rgba(167,139,250,0.45)" },
  { border: "#f97316", bg: "rgba(249,115,22,0.15)", glow: "rgba(249,115,22,0.45)" },
  { border: "#2dd4bf", bg: "rgba(45,212,191,0.15)", glow: "rgba(45,212,191,0.45)" },
  { border: "#f43f5e", bg: "rgba(244,63,94,0.15)", glow: "rgba(244,63,94,0.45)" },
  { border: "#22d3ee", bg: "rgba(34,211,238,0.15)", glow: "rgba(34,211,238,0.45)" },
  { border: "#84cc16", bg: "rgba(132,204,22,0.15)", glow: "rgba(132,204,22,0.45)" },
];

const handles = (
  <>
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
  </>
);

export default function GraphNode({ data, selected }: GraphNodeProps) {
  const brightnessAttribute = data.brightnessAttribute || 'proven_knowledge_rating';
  const thumbnailUrl = data.youtubeThumbnailUrl || null;
  const brightnessValue = toNumber(data[brightnessAttribute], 0);
  const brightness = normalizeValue(brightnessValue, brightnessAttribute);
  const importance = clamp(data.importance);
  const minSize = 80;
  const maxSize = 160;
  const size = minSize + (maxSize - minSize) * importance;

  // ── Chapter node (YouTube video) ──────────────────────────────────────────
  if (data.node_type === "chapter") {
    const paletteIndex = ((data.sequence_number ?? 1) - 1) % CHAPTER_PALETTE.length;
    const palette = CHAPTER_PALETTE[paletteIndex];
    const glowStrength = 10 + brightness * 32;

    return (
      <div
        title={`Video #${data.sequence_number ?? "?"}: ${data.topic_name}`}
        className={`group relative flex flex-col items-center justify-center rounded-full border-2 text-center shadow-sm transition ${selected ? "ring-2 ring-white/50" : ""
          }`}
        style={{
          backgroundColor: palette.bg,
          borderColor: palette.border,
          width: size,
          height: size,
          boxShadow: `0 0 ${glowStrength}px ${palette.glow}, 0 0 ${glowStrength * 2}px ${palette.glow}`,
        }}
      >
        {thumbnailUrl && (
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              data.onOpenVideo?.();
            }}
            className="absolute bottom-full left-1/2 z-20 mb-2 hidden w-32 -translate-x-1/2 overflow-hidden rounded-md border border-border-default bg-bg-surface shadow-lg group-hover:block"
            title="Open video"
          >
            <img
              src={thumbnailUrl}
              alt="YouTube thumbnail preview"
              className="h-20 w-full object-cover"
              loading="lazy"
            />
          </button>
        )}
        <div className="text-xs font-extrabold leading-none" style={{ color: palette.border }}>
          #{data.sequence_number ?? "?"}
        </div>
        <div className="mt-0.5 px-2 w-full text-sm font-semibold font-heading text-white leading-tight line-clamp-4 overflow-hidden text-ellipsis break-words">
          {data.topic_name}
        </div>
        {handles}
      </div>
    );
  }

  // ── Regular topic node ────────────────────────────────────────────────────
  const borderIntensity = clamp(data.forgetting_score);
  const pkr = clamp(toNumber(data.proven_knowledge_rating, 0));
  const boostedBrightness = clamp(brightness * 1.6);
  const backgroundColor = getPKRRgba(pkr, 0.1 + boostedBrightness * 0.85);
  const borderColor = getPKRRgba(pkr, 0.2 + borderIntensity * 0.7);
  const glowStrength = 8 + boostedBrightness * 28;
  const glowOpacity = 0.15 + boostedBrightness * 0.45;
  const glowColor = getPKRRgba(pkr, glowOpacity);

  return (
    <div
      title={`${brightnessAttribute.replace(/_/g, ' ')}: ${brightnessValue.toFixed(2)} | Importance: ${data.importance.toFixed(2)} | Forgetting: ${data.forgetting_score.toFixed(2)}`}
      className={`flex flex-col items-center justify-center rounded-full border-2 text-center text-xs shadow-sm transition ${selected ? "ring-2 ring-border-accent" : ""
        }`}
      style={{
        backgroundColor,
        borderColor,
        width: size,
        height: size,
        boxShadow: `0 0 ${glowStrength}px ${glowColor}, 0 0 ${glowStrength * 1.8}px ${glowColor}`,
      }}
    >
      <div className="px-2 w-full text-sm font-semibold font-heading text-white line-clamp-4 overflow-hidden text-ellipsis break-words">
        {data.topic_name}
      </div>
      {handles}
    </div>
  );
}
