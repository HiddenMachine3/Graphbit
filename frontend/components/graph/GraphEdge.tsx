import { BaseEdge, getStraightPath } from "reactflow";

import type { EdgeProps } from "reactflow";

export default function GraphEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  const edgeType = (data as { edgeType?: string } | undefined)?.edgeType;
  const isMaterialEdge = edgeType === "MATERIAL";

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: isMaterialEdge ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.25)",
          strokeWidth: isMaterialEdge ? 1.4 : 2,
          opacity: 1,
          strokeDasharray: isMaterialEdge ? "6 4" : undefined,
        }}
      />
    </>
  );
}
