import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type MaterialNodeProps = {
  data: GraphNodeDTO & {
    brightnessAttribute?: keyof GraphNodeDTO;
    youtubeThumbnailUrl?: string | null;
    youtubeEmbedUrl?: string | null;
    onOpenVideo?: () => void;
  };
  selected: boolean;
};

export default function MaterialNode({ data, selected }: MaterialNodeProps) {
  const thumbnailUrl = data.youtubeThumbnailUrl || null;

  return (
    <div
      title={`Material: ${data.topic_name}`}
      className={`group relative flex h-14 w-14 flex-col items-center justify-center rounded-2xl border text-center text-xs shadow-sm transition ${
        selected ? "ring-2 ring-border-accent" : ""
      }`}
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        borderColor: "rgba(255, 255, 255, 0.15)",
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
          className="absolute bottom-full left-1/2 z-20 mb-2 hidden w-28 -translate-x-1/2 overflow-hidden rounded-md border border-border-default bg-bg-surface shadow-lg group-hover:block"
          title="Open video"
        >
          <img
            src={thumbnailUrl}
            alt="YouTube thumbnail preview"
            className="h-16 w-full object-cover"
            loading="lazy"
          />
        </button>
      )}
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
