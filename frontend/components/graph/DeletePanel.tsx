'use client';

import { useCallback, useMemo, useState } from 'react';

import type { GraphNodeDTO } from '../../lib/types';
import { deleteNode } from '../../lib/api/graph';

type DeletePanelProps = {
  nodes: GraphNodeDTO[];
  projectId: string | null;
  deleteModeActive: boolean;
  onDeleteModeChange: (active: boolean) => void;
  selectedNodeIds: string[];
  onSelectionChange: (nodeIds: string[]) => void;
  onDeleted: () => void;
};

export default function DeletePanel({
  nodes,
  projectId,
  deleteModeActive,
  onDeleteModeChange,
  selectedNodeIds,
  onSelectionChange,
  onDeleted,
}: DeletePanelProps) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedNodes = useMemo(
    () => selectedNodeIds.map((id) => nodes.find((node) => node.id === id)).filter(Boolean),
    [selectedNodeIds, nodes]
  );

  const startDeleteMode = () => {
    setError(null);
    onSelectionChange([]);
    onDeleteModeChange(true);
  };

  const cancelDeleteMode = () => {
    setError(null);
    onSelectionChange([]);
    onDeleteModeChange(false);
  };

  const handleDeleteSelected = useCallback(async () => {
    if (!projectId) {
      setError('Select a project first');
      return;
    }
    if (selectedNodes.length === 0) {
      setError('Select nodes to delete');
      return;
    }

    if (!window.confirm(`Delete ${selectedNodes.length} selected node(s)?`)) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      for (const node of selectedNodes) {
        const mode = node.id.startsWith('chapter_') ? 'cascade' : 'single';
        await deleteNode(projectId, node.id, mode);
      }
      onSelectionChange([]);
      onDeleteModeChange(false);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete nodes');
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedNodes, onSelectionChange, onDeleteModeChange, onDeleted]);

  return (
    <div className='rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-slate-200'>
      <h3 className='font-semibold text-white'>Delete Nodes</h3>

      {error && (
        <div className='mt-2 rounded border border-red-900/60 bg-red-950/40 p-2 text-xs text-red-200'>
          {error}
        </div>
      )}

      {!deleteModeActive && (
        <div className='mt-3 space-y-2'>
          <button
            className='w-full rounded bg-rose-600 px-3 py-2 text-xs text-white hover:bg-rose-700 disabled:opacity-60'
            onClick={startDeleteMode}
            disabled={loading}
          >
            Click nodes to delete
          </button>
          <p className='text-xs text-slate-400'>Main nodes will delete connected topic nodes.</p>
        </div>
      )}

      {deleteModeActive && (
        <div className='mt-3 space-y-3'>
          <div className='rounded border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-200'>
            <p className='font-medium text-rose-200'>Delete mode: Select nodes</p>
            <p className='mt-1'>Click nodes in the graph to add or remove them.</p>
            <div className='mt-2 space-y-1'>
              {selectedNodes.length === 0 && <div className='text-slate-400'>No nodes selected</div>}
              {selectedNodes.map((node, index) => (
                <div key={node.id} className='text-xs'>
                  {index + 1}. {node.topic_name}
                </div>
              ))}
            </div>
          </div>

          <div className='flex gap-2'>
            <button
              className='flex-1 rounded bg-rose-600 px-2 py-1 text-xs text-white hover:bg-rose-700 disabled:opacity-60'
              onClick={handleDeleteSelected}
              disabled={loading || selectedNodes.length === 0}
            >
              Delete Selected
            </button>
            <button
              className='flex-1 rounded bg-slate-700 px-2 py-1 text-xs text-white hover:bg-slate-600 disabled:opacity-60'
              onClick={cancelDeleteMode}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
