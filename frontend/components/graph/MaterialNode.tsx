import { Handle, Position } from "reactflow";

import type { GraphNodeDTO } from "../../lib/types";

type MaterialNodeProps = {
  data: GraphNodeDTO & {
    brightnessAttribute?: keyof GraphNodeDTO;
    youtubeThumbnailUrl?: string | null;
    youtubeEmbedUrl?: string | null;
    materialId?: string | null;
    sourceUrl?: string | null;
    onOpenRead?: () => void;
    onOpenSource?: () => void;
    onOpenVideo?: () => void;
    isExpanded?: boolean;
    hasChildren?: boolean;
    onToggleExpand?: (nodeId: string) => void;
  };
  selected: boolean;
};

export default function MaterialNode({ data, selected }: MaterialNodeProps) {
  const hasYoutubeVideo = Boolean(data.youtubeEmbedUrl);
  const hasReadableMaterial = Boolean(data.materialId && data.onOpenRead);

  return (
    <div
      title={`Material: ${data.topic_name}`}
      className={`group relative flex h-24 w-24 flex-col items-center justify-center rounded-2xl border text-center text-xs shadow-sm transition ${selected ? "ring-2 ring-border-accent" : ""
        }`}
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        borderColor: "rgba(255, 255, 255, 0.15)",
      }}
    >
      {selected && (
        <div className="absolute left-1/2 top-full z-20 mt-2 flex -translate-x-1/2 items-center gap-1">
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              data.onOpenRead?.();
            }}
            disabled={!hasReadableMaterial}
            className="rounded border border-border-default bg-bg-surface px-2 py-0.5 text-[10px] font-semibold font-body text-text-secondary shadow-sm hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-60"
            title={hasReadableMaterial ? "Read material notes" : "No readable material available"}
          >
            Read
          </button>
          {hasYoutubeVideo && (
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                data.onOpenVideo?.();
              }}
              className="rounded border border-border-default bg-bg-surface px-2 py-0.5 text-[10px] font-semibold font-body text-text-secondary shadow-sm hover:bg-bg-hover"
              title="View linked YouTube video"
            >
              View
            </button>
          )}
        </div>
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
