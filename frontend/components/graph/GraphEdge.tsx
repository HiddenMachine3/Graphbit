import { BaseEdge, getStraightPath, useStore } from "reactflow";

import type { EdgeProps } from "reactflow";

function getNodeRadius(node: { id: string; data?: { importance?: number } }) {
  const isChapterNode = node.id.startsWith("chapter_");
  if (isChapterNode) {
    return 7;
  }
  const importance = Math.min(1, Math.max(0, node.data?.importance ?? 0.5));
  const size = 18 + 18 * importance;
  return size / 2;
}

export default function GraphEdge({
  id,
  source,
  target,
  sourceX,
  sourceY,
  targetX,
  targetY,
}: EdgeProps) {
  const sourceNode = useStore((state) => state.nodeInternals.get(source));
  const targetNode = useStore((state) => state.nodeInternals.get(target));

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const distance = Math.hypot(dx, dy) || 1;
  const sourceRadius = sourceNode ? getNodeRadius(sourceNode) : 8;
  const targetRadius = targetNode ? getNodeRadius(targetNode) : 8;
  const sourceTrim = sourceRadius + 2;
  const targetTrim = targetRadius + 2;

  const trimmedSourceX = sourceX + (dx / distance) * sourceTrim;
  const trimmedSourceY = sourceY + (dy / distance) * sourceTrim;
  const trimmedTargetX = targetX - (dx / distance) * targetTrim;
  const trimmedTargetY = targetY - (dy / distance) * targetTrim;

  const [edgePath] = getStraightPath({
    sourceX: trimmedSourceX,
    sourceY: trimmedSourceY,
    targetX: trimmedTargetX,
    targetY: trimmedTargetY,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: "rgba(226, 232, 240, 0.7)",
          strokeWidth: 1.2,
          strokeLinecap: "round",
        }}
      />
    </>
  );
}
