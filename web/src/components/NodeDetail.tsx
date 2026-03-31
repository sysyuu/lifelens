import React, { useState, useEffect } from 'react';
import { NodeRunData, NodeConfigData } from '../types';
import { useApi } from '../hooks/useApi';

interface NodeDetailProps {
  nodeRun: NodeRunData | null;
  nodeId: string;
  workflowRunId: string | null;
  profileId: string;
  onRerun: () => void;
}

const AVAILABLE_MODELS = [
  'Claude-Opus-4.6',
  'Claude-Sonnet-4.6',
  'Claude-Haiku-4.5',
  'Gemini-2.5-Pro',
  'Gemini-2.5-Flash',
  'GPT-4.1',
];

export default function NodeDetail({ nodeRun, nodeId, workflowRunId, profileId, onRerun }: NodeDetailProps) {
  const api = useApi(profileId);
  const [config, setConfig] = useState<NodeConfigData | null>(null);
  const [editingPrompt, setEditingPrompt] = useState('');
  const [editingModel, setEditingModel] = useState('');
  const [saving, setSaving] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'input' | 'output' | 'config'>('output');

  useEffect(() => {
    api.getNodeConfig(nodeId).then(setConfig).catch(console.error);
  }, [nodeId]);

  useEffect(() => {
    if (config) {
      setEditingPrompt(config.effective.system_prompt || '');
      setEditingModel(config.effective.model || '');
    }
  }, [config]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateNodeConfig(nodeId, {
        model: editingModel || undefined,
        system_prompt: editingPrompt || undefined,
      });
      const updated = await api.getNodeConfig(nodeId);
      setConfig(updated);
    } catch (err) {
      console.error('Failed to save config:', err);
    }
    setSaving(false);
  };

  const handleRerun = async () => {
    if (!workflowRunId) return;
    setRerunning(true);
    try {
      await api.rerunNode(workflowRunId, nodeId);
      onRerun();
    } catch (err) {
      console.error('Failed to rerun node:', err);
    }
    setRerunning(false);
  };

  const statusStyle: Record<string, { bg: string; text: string }> = {
    completed: { bg: '#dcfce7', text: '#166534' },
    failed: { bg: '#fef2f2', text: '#991b1b' },
    running: { bg: '#dbeafe', text: '#1e40af' },
    pending: { bg: '#f3f4f6', text: '#374151' },
  };

  const status = nodeRun?.status || 'pending';
  const colors = statusStyle[status] || statusStyle.pending;

  return (
    <div style={{ padding: 20, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>
          节点：{nodeRun?.node_name || nodeId}
        </h3>
        <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 13 }}>
          <span
            style={{
              padding: '2px 10px',
              borderRadius: 12,
              backgroundColor: colors.bg,
              color: colors.text,
              fontWeight: 500,
            }}
          >
            {status === 'completed' ? '✅ 已完成' :
             status === 'failed' ? '❌ 失败' :
             status === 'running' ? '🔄 运行中' : '⏳ 等待中'}
          </span>
          {nodeRun?.duration_seconds && (
            <span style={{ color: '#6b7280' }}>
              耗时：{nodeRun.duration_seconds.toFixed(1)}s
            </span>
          )}
          {nodeRun?.token_usage && (
            <span style={{ color: '#6b7280' }}>
              Token：{nodeRun.token_usage.total_tokens?.toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #e5e7eb', marginBottom: 16 }}>
        {(['input', 'output', 'config'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #3b82f6' : '2px solid transparent',
              background: 'none',
              cursor: 'pointer',
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? '#3b82f6' : '#6b7280',
              fontSize: 14,
            }}
          >
            {tab === 'input' ? '输入' : tab === 'output' ? '输出' : '配置'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'input' && (
        <div>
          <h4 style={{ fontSize: 14, marginBottom: 8 }}>输入数据</h4>
          <pre
            style={{
              backgroundColor: '#f9fafb',
              padding: 12,
              borderRadius: 8,
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 500,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {nodeRun?.input_data
              ? JSON.stringify(nodeRun.input_data, null, 2)
              : '暂无输入数据'}
          </pre>
        </div>
      )}

      {activeTab === 'output' && (
        <div>
          <h4 style={{ fontSize: 14, marginBottom: 8 }}>输出数据</h4>
          {nodeRun?.error_message && (
            <div
              style={{
                backgroundColor: '#fef2f2',
                padding: 12,
                borderRadius: 8,
                marginBottom: 12,
                color: '#991b1b',
                fontSize: 13,
              }}
            >
              错误：{nodeRun.error_message}
            </div>
          )}
          <pre
            style={{
              backgroundColor: '#f9fafb',
              padding: 12,
              borderRadius: 8,
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 500,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {nodeRun?.output_data
              ? JSON.stringify(nodeRun.output_data, null, 2)
              : '暂无输出数据'}
          </pre>
        </div>
      )}

      {activeTab === 'config' && (
        <div>
          {/* Model selector */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
              模型
            </label>
            <select
              value={editingModel}
              onChange={(e) => setEditingModel(e.target.value)}
              style={{
                width: '100%',
                padding: 8,
                borderRadius: 6,
                border: '1px solid #d1d5db',
                fontSize: 13,
              }}
            >
              <option value="">（默认）</option>
              {AVAILABLE_MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* System Prompt editor */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
              System Prompt
            </label>
            <textarea
              value={editingPrompt}
              onChange={(e) => setEditingPrompt(e.target.value)}
              rows={20}
              style={{
                width: '100%',
                padding: 8,
                borderRadius: 6,
                border: '1px solid #d1d5db',
                fontSize: 12,
                fontFamily: 'monospace',
                resize: 'vertical',
              }}
            />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: '8px 20px',
                backgroundColor: '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: saving ? 'not-allowed' : 'pointer',
                fontSize: 13,
              }}
            >
              {saving ? '保存中...' : '保存配置'}
            </button>
            <button
              onClick={handleRerun}
              disabled={rerunning || !workflowRunId}
              style={{
                padding: '8px 20px',
                backgroundColor: '#f59e0b',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: rerunning ? 'not-allowed' : 'pointer',
                fontSize: 13,
              }}
            >
              {rerunning ? '运行中...' : '重新运行此节点'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
