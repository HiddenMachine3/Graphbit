import { BaseEdge, EdgeLabelRenderer, getStraightPath } from "reactflow";

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
          stroke: isMaterialEdge ? "#d96a87" : "#8a1b3c",
          strokeWidth: isMaterialEdge ? 1.2 : 1,
          opacity: isMaterialEdge ? 0.55 : 0.35,
          strokeDasharray: isMaterialEdge ? "6 4" : undefined,
        }}
      />
      <EdgeLabelRenderer />
    </>
  );
}
