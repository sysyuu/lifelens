import React, { useState, useEffect } from 'react';
import { NodeRunData, NodeConfigData } from '../types';
import { useApi } from '../hooks/useApi';

interface NodeDetailProps {
  nodeRun: NodeRunData | null;
  nodeId: string;
  workflowRunId: string | null;
  profileId: string;
  onRerun: () => void;
  allNodeRuns?: NodeRunData[];
}

const AVAILABLE_MODELS = [
  'Claude-Opus-4.6',
  'Claude-Sonnet-4.6',
  'Claude-Haiku-4.5',
  'Gemini-2.5-Pro',
  'Gemini-2.5-Flash',
  'GPT-4.1',
];

const NODE_DESCRIPTIONS: Record<string, string> = {
  '1.1_video_preprocess': 'FFmpeg 提取音频、生成缩略图、获取视频元数据',
  '1.2_visual_understanding': 'Gemini 2.5 Pro 分析视频画面内容（场景、人物、活动）',
  '1.3a_speaker_diarization': '说话人分离与声纹匹配',
  '1.3b_asr': '语音转文字（FunASR / Whisper）',
  '1.3c_emotion_recognition': '情绪识别（emotion2vec）',
  '2.1_event_structuring': 'Claude Opus 将视频片段整合为连贯事件',
  '2.2_person_matching': 'Claude Sonnet 匹配视频中的人物与社交圈',
  '3.1_profile_update': 'Claude Opus 根据今日事件更新用户画像',
  '3.2_diary_generation': 'Claude Opus 生成个性化日记',
  '4.1_media_slicing': 'FFmpeg 裁剪关键帧和视频片段',
  '4.2_quality_check': 'Claude Sonnet 检查日记质量',
  '4.3_storage': '将日记、事件、媒体、画像更新写入数据库',
};

const NODE_DEPS: Record<string, string[]> = {
  '1.2_visual_understanding': ['1.1_video_preprocess'],
  '1.3a_speaker_diarization': ['1.1_video_preprocess'],
  '1.3b_asr': ['1.3a_speaker_diarization'],
  '1.3c_emotion_recognition': ['1.3a_speaker_diarization'],
  '2.1_event_structuring': ['1.2_visual_understanding', '1.3b_asr', '1.3c_emotion_recognition'],
  '2.2_person_matching': ['2.1_event_structuring'],
  '3.1_profile_update': ['2.2_person_matching'],
  '3.2_diary_generation': ['3.1_profile_update'],
  '4.1_media_slicing': ['3.2_diary_generation'],
  '4.2_quality_check': ['4.1_media_slicing'],
  '4.3_storage': ['4.2_quality_check'],
};

export default function NodeDetail({ nodeRun, nodeId, workflowRunId, profileId, onRerun, allNodeRuns = [] }: NodeDetailProps) {
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
        {/* Description */}
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>
          {NODE_DESCRIPTIONS[nodeId] || ''}
        </div>
        {/* Waiting info for pending nodes */}
        {status === 'pending' && (() => {
          const deps = NODE_DEPS[nodeId] || [];
          const runMap: Record<string, NodeRunData> = {};
          allNodeRuns.forEach((nr) => { runMap[nr.node_id] = nr; });
          const incomplete = deps.filter((d) => !runMap[d] || runMap[d].status !== 'completed');
          if (incomplete.length > 0) {
            return (
              <div style={{ fontSize: 12, color: '#d97706', marginTop: 6, backgroundColor: '#fffbeb', padding: '6px 10px', borderRadius: 6 }}>
                等待上游节点完成：{incomplete.map((d) => {
                  const nr = runMap[d];
                  const depStatus = nr?.status || 'pending';
                  return `${nr?.node_name || d}(${depStatus === 'running' ? '运行中' : '等待中'})`;
                }).join('、')}
              </div>
            );
          }
          return null;
        })()}
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
