import { useCallback, useState } from "react";

import type { GraphNodeDTO } from "../../lib/types";
import { deleteNode } from "../../lib/api/graph";

type NodeDetailPanelProps = {
  node: GraphNodeDTO | null;
  projectId: string | null;
  onEdit?: () => void;
  onDeleted?: () => void;
};

export default function NodeDetailPanel({
  node,
  projectId,
  onEdit,
  onDeleted,
}: NodeDetailPanelProps) {
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  if (!node) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
        Select a node to see details.
      </div>
    );
  }

  const isChapterNode = node.id.startsWith("chapter_");

  const handleDelete = useCallback(
    async (mode: "single" | "cascade") => {
      if (!projectId) {
        setDeleteError("Select a project first");
        return;
      }

      const confirmMessage =
        mode === "cascade"
          ? "Delete this main node and its connected topic nodes?"
          : "Delete this node?";

      if (!window.confirm(confirmMessage)) {
        return;
      }

      setDeleting(true);
      setDeleteError(null);
      try {
        await deleteNode(projectId, node.id, mode);
        onDeleted?.();
      } catch (err) {
        setDeleteError(err instanceof Error ? err.message : "Failed to delete node");
      } finally {
        setDeleting(false);
      }
    },
    [projectId, node.id, onDeleted]
  );

  const handleDeleteSelected = useCallback(() => {
    handleDelete(isChapterNode ? "cascade" : "single");
  }, [handleDelete, isChapterNode]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">
      <div className="flex items-start justify-between">
        <div className="text-base font-semibold text-white">{node.topic_name}</div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-xs font-medium text-rose-300 hover:text-rose-200"
            title="Edit node properties"
          >
            ✎
          </button>
        )}
      </div>
      {deleteError && (
        <div className="mt-3 rounded border border-red-900/60 bg-red-950/40 p-2 text-xs text-red-200">
          {deleteError}
        </div>
      )}
      <div className="mt-2 space-y-1">
        <div>PKR: {node.proven_knowledge_rating.toFixed(2)}</div>
        <div>Forgetting: {node.forgetting_score.toFixed(2)}</div>
        <div>Linked questions: {node.linked_questions_count}</div>
        <div>Linked materials: {node.linked_materials_count}</div>
      </div>
      <div className="mt-4">
        <button
          className="w-full rounded bg-rose-600 px-3 py-2 text-xs text-white hover:bg-rose-700 disabled:opacity-60"
          onClick={handleDeleteSelected}
          disabled={deleting}
        >
          {isChapterNode ? "Delete Main Node (and topics)" : "Delete Node"}
        </button>
      </div>
    </div>
  );
}
