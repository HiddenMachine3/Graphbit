'use client';

import { useState, useCallback, useEffect } from 'react';
import type { GraphNodeDTO } from '../../lib/types';
import { createEdge } from '../../lib/api/graph';

type EdgeManagementPanelProps = {
  nodes: GraphNodeDTO[];
  selectedNodeId: string | null;
  onEdgeCreated: () => void;
  clickModeActive?: boolean;
  onClickModeChange?: (active: boolean) => void;
  selectedNodesForEdge?: string[];
  onNodesChange?: (nodes: string[]) => void;
};

export default function EdgeManagementPanel({
  nodes,
  selectedNodeId,
  onEdgeCreated,
  clickModeActive = false,
  onClickModeChange,
  selectedNodesForEdge = [],
  onNodesChange,
}: EdgeManagementPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [fromNodeId, setFromNodeId] = useState(selectedNodeId || '');
  const [toNodeId, setToNodeId] = useState('');
  const [edgeType, setEdgeType] = useState('PREREQUISITE');
  const [weight, setWeight] = useState(1.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update fromNodeId when selectedNodeId changes
  useEffect(() => {
    if (!clickModeActive) {
      setFromNodeId(selectedNodeId || '');
    }
  }, [selectedNodeId, clickModeActive]);

  const handleCreateEdge = useCallback(async () => {
    // Use selectedNodesForEdge in click mode, otherwise use form fields
    const from = clickModeActive ? selectedNodesForEdge[0] : fromNodeId;
    const to = clickModeActive ? selectedNodesForEdge[1] : toNodeId;

    if (!from || !to) {
      setError('Both nodes must be selected');
      return;
    }
    if (from === to) {
      setError('Cannot connect a node to itself');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await createEdge(from, to, edgeType, weight);
      setToNodeId('');
      setEdgeType('PREREQUISITE');
      setWeight(1.0);
      setShowForm(false);
      if (onClickModeChange) {
        onClickModeChange(false);
      }
      if (onNodesChange) {
        onNodesChange([]);
      }
      onEdgeCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create connection');
    } finally {
      setLoading(false);
    }
  }, [clickModeActive, selectedNodesForEdge, fromNodeId, toNodeId, edgeType, weight, onEdgeCreated, onClickModeChange, onNodesChange]);

  const handleNodeClick = (nodeId: string) => {
    if (!onNodesChange) return;
    
    if (selectedNodesForEdge.includes(nodeId)) {
      onNodesChange(selectedNodesForEdge.filter(id => id !== nodeId));
    } else if (selectedNodesForEdge.length < 2) {
      const newClicked = [...selectedNodesForEdge, nodeId];
      onNodesChange(newClicked);
      
      if (newClicked.length === 2) {
        setFromNodeId(newClicked[0]);
        setToNodeId(newClicked[1]);
      }
    }
  };

  const startClickMode = () => {
    if (onNodesChange) {
      onNodesChange([]);
    }
    setFromNodeId('');
    setToNodeId('');
    if (onClickModeChange) {
      onClickModeChange(true);
    }
    setShowForm(false);
  };

  const cancelClickMode = () => {
    if (onClickModeChange) {
      onClickModeChange(false);
    }
    if (onNodesChange) {
      onNodesChange([]);
    }
    setFromNodeId('');
    setToNodeId('');
  };

  return (
    <div className='rounded border border-slate-200 bg-white p-4'>
      <h3 className='font-semibold text-slate-900'>Add Connection</h3>

      {error && (
        <div className='mt-2 rounded bg-red-50 p-2 text-xs text-red-700'>
          {error}
        </div>
      )}

      {!showForm && !clickModeActive && (
        <div className='mt-3 space-y-2'>
          <button
            className='w-full rounded bg-green-600 px-3 py-2 text-xs text-white hover:bg-green-700 disabled:opacity-60'
            onClick={startClickMode}
            disabled={loading}
          >
            Click nodes to connect
          </button>
          <button
            className='w-full rounded bg-slate-600 px-3 py-2 text-xs text-white hover:bg-slate-700 disabled:opacity-60'
            onClick={() => { setShowForm(true); }}
            disabled={loading}
          >
            Manual connection
          </button>
        </div>
      )}

      {clickModeActive && (
        <div className='mt-3'>
          <div className='rounded bg-blue-50 p-3 text-xs text-blue-700'>
            <p className='font-medium'>Click mode: Select 2 nodes</p>
            <p className='mt-1'>
              {selectedNodesForEdge.length === 0 && 'Click first node...'}
              {selectedNodesForEdge.length === 1 && 'Click second node...'}
              {selectedNodesForEdge.length === 2 && 'Two nodes selected! Set attributes below.'}
            </p>
            <div className='mt-2 space-y-1'>
              {selectedNodesForEdge.map((id, i) => (
                <div key={id} className='text-xs'>
                  {i + 1}. {nodes.find(n => n.id === id)?.topic_name || id}
                  <button
                    onClick={() => handleNodeClick(id)}
                    className='ml-2 text-blue-600 hover:text-blue-800'
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          {selectedNodesForEdge.length === 2 && (
            <div className='mt-3 space-y-2'>
              <div>
                <label className='block text-xs font-medium text-slate-700'>
                  Relationship Type
                </label>
                <select
                  value={edgeType}
                  onChange={(e) => setEdgeType(e.target.value)}
                  className='mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs'
                  disabled={loading}
                >
                  <option value='PREREQUISITE'>Prerequisite</option>
                  <option value='DEPENDS_ON'>Depends On</option>
                  <option value='APPLIED_WITH'>Applied With</option>
                  <option value='SUBCONCEPT_OF'>Subconcept Of</option>
                </select>
              </div>

              <div className='space-y-1'>
                <label className='block text-xs text-slate-600'>
                  Strength: {weight.toFixed(2)}
                </label>
                <input
                  type='range'
                  min='0'
                  max='1'
                  step='0.1'
                  value={weight}
                  onChange={(e) => setWeight(parseFloat(e.target.value))}
                  className='w-full'
                  disabled={loading}
                />
              </div>

              <div className='flex gap-2'>
                <button
                  className='flex-1 rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-60'
                  onClick={handleCreateEdge}
                  disabled={loading}
                >
                  Create
                </button>
                <button
                  className='flex-1 rounded bg-slate-400 px-2 py-1 text-xs text-white hover:bg-slate-500 disabled:opacity-60'
                  onClick={cancelClickMode}
                  disabled={loading}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {selectedNodesForEdge.length < 2 && (
            <div className='mt-3 flex gap-2'>
              <button
                className='flex-1 rounded bg-slate-400 px-2 py-1 text-xs text-white hover:bg-slate-500 disabled:opacity-60'
                onClick={cancelClickMode}
                disabled={loading}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}

      {showForm && (
        <div className='mt-3 space-y-2'>
          <div>
            <label className='block text-xs font-medium text-slate-700'>
              From Node
            </label>
            <select
              value={fromNodeId}
              onChange={(e) => setFromNodeId(e.target.value)}
              className='mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs'
              disabled={loading}
            >
              <option value=''>Select node...</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.topic_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className='block text-xs font-medium text-slate-700'>
              To Node
            </label>
            <select
              value={toNodeId}
              onChange={(e) => setToNodeId(e.target.value)}
              className='mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs'
              disabled={loading}
            >
              <option value=''>Select node...</option>
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.topic_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className='block text-xs font-medium text-slate-700'>
              Relationship Type
            </label>
            <select
              value={edgeType}
              onChange={(e) => setEdgeType(e.target.value)}
              className='mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs'
              disabled={loading}
            >
              <option value='PREREQUISITE'>Prerequisite</option>
              <option value='DEPENDS_ON'>Depends On</option>
              <option value='APPLIED_WITH'>Applied With</option>
              <option value='SUBCONCEPT_OF'>Subconcept Of</option>
            </select>
          </div>

          <div className='space-y-1'>
            <label className='block text-xs text-slate-600'>
              Strength: {weight.toFixed(2)}
            </label>
            <input
              type='range'
              min='0'
              max='1'
              step='0.1'
              value={weight}
              onChange={(e) => setWeight(parseFloat(e.target.value))}
              className='w-full'
              disabled={loading}
            />
          </div>

          <div className='flex gap-2'>
            <button
              className='flex-1 rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-60'
              onClick={handleCreateEdge}
              disabled={loading || !fromNodeId || !toNodeId}
            >
              Create
            </button>
            <button
              className='flex-1 rounded bg-slate-400 px-2 py-1 text-xs text-white hover:bg-slate-500 disabled:opacity-60'
              onClick={() => setShowForm(false)}
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
