import { BaseEdge, getSmoothStepPath, getStraightPath } from "reactflow";

import type { EdgeProps } from "reactflow";

export default function GraphEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const edgeType = (data as { edgeType?: string } | undefined)?.edgeType;
  const isMaterialEdge = edgeType === "MATERIAL";
  const isSequenceEdge = edgeType === "VIDEO_SEQUENCE";

  const [edgePath] = isSequenceEdge
    ? getSmoothStepPath({ sourceX, sourceY, targetX, targetY, borderRadius: 16 })
    : getStraightPath({ sourceX, sourceY, targetX, targetY });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: isSequenceEdge
            ? "rgba(255,255,255,0.70)"
            : isMaterialEdge
            ? "rgba(255, 255, 255, 0.12)"
            : "rgba(255, 255, 255, 0.25)",
          strokeWidth: isSequenceEdge ? 2.5 : isMaterialEdge ? 1.4 : 2,
          strokeDasharray: isSequenceEdge ? "10 5" : isMaterialEdge ? "6 4" : undefined,
          opacity: 1,
        }}
      />
    </>
  );
}
