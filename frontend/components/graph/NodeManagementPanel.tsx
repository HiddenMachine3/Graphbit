'use client';

import { useState, useCallback } from 'react';
import type { GraphNodeDTO } from '../../lib/types';
import { createNode, updateNode } from '../../lib/api/graph';

type NodeManagementPanelProps = {
  selectedNode: GraphNodeDTO | null;
  projectId: string | null;
  onNodeCreated: () => void;
  onNodeUpdated: () => void;
};

export default function NodeManagementPanel({
  selectedNode,
  projectId,
  onNodeCreated,
  onNodeUpdated,
}: NodeManagementPanelProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [newTopicName, setNewTopicName] = useState('');
  const [newImportance, setNewImportance] = useState(0.5);
  const [newRelevance, setNewRelevance] = useState(0.5);
  const [editedTopic, setEditedTopic] = useState('');
  const [editedImportance, setEditedImportance] = useState(0.5);
  const [editedRelevance, setEditedRelevance] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateNode = useCallback(async () => {
    if (!projectId) {
      setError('Select a project first');
      return;
    }
    if (!newTopicName.trim()) {
      setError('Topic name is required');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await createNode(projectId, newTopicName, newImportance, newRelevance);
      setNewTopicName('');
      setNewImportance(0.5);
      setNewRelevance(0.5);
      setShowCreateForm(false);
      onNodeCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create node');
    } finally {
      setLoading(false);
    }
  }, [newTopicName, newImportance, newRelevance, onNodeCreated]);

  const handleUpdateNode = useCallback(async () => {
    if (!selectedNode || !projectId) return;

    setLoading(true);
    setError(null);
    try {
      await updateNode(projectId, selectedNode.id, {
        topic_name: editedTopic || selectedNode.topic_name,
        importance: editedImportance,
        relevance: editedRelevance,
      });
      setShowEditForm(false);
      onNodeUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update node');
    } finally {
      setLoading(false);
    }
  }, [selectedNode, projectId, editedTopic, editedImportance, editedRelevance, onNodeUpdated]);

  const openEditForm = () => {
    if (selectedNode) {
      setEditedTopic(selectedNode.topic_name);
      setEditedImportance(selectedNode.importance);
      setEditedRelevance(selectedNode.relevance);
      setShowEditForm(true);
    }
  };

  return (
    <div className='rounded-2xl border border-border-default bg-bg-surface p-4 text-text-primary'>
      <h3 className='font-semibold font-heading text-white'>
        {selectedNode ? 'Edit Node' : 'Add Node'}
      </h3>

      {error && (
        <div className='mt-2 rounded border border-pkr-low/30 bg-pkr-low/10 p-2 text-xs font-body text-pkr-low'>
          {error}
        </div>
      )}

      {!showCreateForm && !showEditForm && (
        <div className='mt-3 space-y-2'>
          <button
            className='w-full rounded bg-accent px-3 py-2 text-xs font-semibold font-body text-white hover:bg-accent-hover disabled:opacity-60'
            disabled={loading || !projectId}
          >
            + Add New Node
          </button>
          {selectedNode && (
            <button
              className='w-full rounded bg-bg-elevated border border-border-default px-3 py-2 text-xs font-semibold font-body text-text-primary hover:bg-bg-hover disabled:opacity-60'
              onClick={openEditForm}
              disabled={loading}
            >
              ✎ Edit Selected Node
            </button>
          )}
        </div>
      )}

      {showCreateForm && (
        <div className='mt-3 space-y-2'>
          <input
            type='text'
            placeholder='Topic name'
            value={newTopicName}
            onChange={(e) => setNewTopicName(e.target.value)}
            className='w-full rounded border border-border-default bg-bg-elevated px-2 py-1 text-xs font-body text-text-primary placeholder:text-text-muted focus:border-accent-dim'
            disabled={loading}
          />
          <div className='space-y-1'>
            <label className='block text-xs font-medium font-body text-text-secondary'>
              Importance: {newImportance.toFixed(2)}
            </label>
            <input
              type='range'
              min='0'
              max='1'
              step='0.1'
              value={newImportance}
              onChange={(e) => setNewImportance(parseFloat(e.target.value))}
              className='w-full'
              disabled={loading}
            />
          </div>
          <div className='space-y-1'>
            <label className='block text-xs font-medium font-body text-text-secondary'>
              Relevance: {newRelevance.toFixed(2)}
            </label>
            <input
              type='range'
              min='0'
              max='1'
              step='0.1'
              value={newRelevance}
              onChange={(e) => setNewRelevance(parseFloat(e.target.value))}
              className='w-full'
              disabled={loading}
            />
          </div>
          <div className='flex gap-2'>
            <button
              className='flex-1 rounded bg-accent px-2 py-1 text-xs font-semibold font-body text-white hover:bg-accent-hover disabled:opacity-60'
              onClick={handleCreateNode}
              disabled={loading}
            >
              Create
            </button>
            <button
              className='flex-1 rounded bg-bg-elevated border border-border-default px-2 py-1 text-xs font-semibold font-body text-text-primary hover:bg-bg-hover disabled:opacity-60'
              onClick={() => setShowCreateForm(false)}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {showEditForm && selectedNode && (
        <div className='mt-3 space-y-2'>
          <input
            type='text'
            placeholder='Topic name'
            value={editedTopic}
            onChange={(e) => setEditedTopic(e.target.value)}
            className='w-full rounded border border-border-default bg-bg-elevated px-2 py-1 text-xs font-body text-text-primary placeholder:text-text-muted focus:border-accent-dim'
            disabled={loading}
          />
          <div className='space-y-1'>
            <label className='block text-xs font-medium font-body text-text-secondary'>
              Importance: {editedImportance.toFixed(2)}
            </label>
            <input
              type='range'
              min='0'
              max='1'
              step='0.1'
              value={editedImportance}
              onChange={(e) => setEditedImportance(parseFloat(e.target.value))}
              className='w-full'
              disabled={loading}
            />
          </div>
          <div className='space-y-1'>
            <label className='block text-xs font-medium font-body text-text-secondary'>
              Relevance: {editedRelevance.toFixed(2)}
            </label>
            <input
              type='range'
              min='0'
              max='1'
              step='0.1'
              value={editedRelevance}
              onChange={(e) => setEditedRelevance(parseFloat(e.target.value))}
              className='w-full'
              disabled={loading}
            />
          </div>
          <div className='flex gap-2'>
            <button
              className='flex-1 rounded bg-accent px-2 py-1 text-xs font-semibold font-body text-white hover:bg-accent-hover disabled:opacity-60'
              onClick={handleUpdateNode}
              disabled={loading}
            >
              Update
            </button>
            <button
              className='flex-1 rounded bg-bg-elevated border border-border-default px-2 py-1 text-xs font-semibold font-body text-text-primary hover:bg-bg-hover disabled:opacity-60'
              onClick={() => setShowEditForm(false)}
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
