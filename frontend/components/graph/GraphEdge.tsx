import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "reactflow";

import type { EdgeProps } from "reactflow";

export default function GraphEdge({ id, sourceX, sourceY, targetX, targetY }: EdgeProps) {
  const [edgePath] = getBezierPath({
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
        style={{ stroke: "#64748b", strokeWidth: 1, opacity: 0.35 }}
      />
      <EdgeLabelRenderer />
    </>
  );
}
