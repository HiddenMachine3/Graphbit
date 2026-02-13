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
          stroke: isMaterialEdge ? "#d96a87" : "#b0274d",
          strokeWidth: isMaterialEdge ? 1.4 : 2,
          opacity: isMaterialEdge ? 0.65 : 0.8,
          strokeDasharray: isMaterialEdge ? "6 4" : undefined,
        }}
      />
    </>
  );
}
