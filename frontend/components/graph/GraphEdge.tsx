import { BaseEdge, EdgeLabelRenderer, getStraightPath } from "reactflow";

import type { EdgeProps } from "reactflow";

export default function GraphEdge({ id, sourceX, sourceY, targetX, targetY }: EdgeProps) {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ stroke: "#8a1b3c", strokeWidth: 1, opacity: 0.35 }}
      />
      <EdgeLabelRenderer />
    </>
  );
}
