import React, { useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  NodeProps,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NodeRunData } from '../types';

interface WorkflowDAGProps {
  nodeRuns: NodeRunData[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string) => void;
}

// Pipeline definition matching the backend
const PIPELINE_NODES = [
  { id: '1.1_video_preprocess', name: '视频预处理', x: 250, y: 0 },
  { id: '1.2_visual_understanding', name: '画面理解', x: 100, y: 100 },
  { id: '1.3a_speaker_diarization', name: '说话人分离', x: 400, y: 100 },
  { id: '1.3b_asr', name: '语音转文字', x: 320, y: 200 },
  { id: '1.3c_emotion_recognition', name: '情绪识别', x: 480, y: 200 },
  { id: '2.1_event_structuring', name: '事件结构化', x: 250, y: 310 },
  { id: '2.2_person_matching', name: '人物匹配', x: 250, y: 410 },
  { id: '3.1_profile_update', name: '画像更新', x: 250, y: 510 },
  { id: '3.2_diary_generation', name: '日记生成', x: 250, y: 610 },
  { id: '4.1_media_slicing', name: '媒体切片', x: 250, y: 710 },
  { id: '4.2_quality_check', name: '质量检查', x: 250, y: 810 },
  { id: '4.3_storage', name: '存储', x: 250, y: 910 },
];

const PIPELINE_EDGES = [
  { source: '1.1_video_preprocess', target: '1.2_visual_understanding' },
  { source: '1.1_video_preprocess', target: '1.3a_speaker_diarization' },
  { source: '1.3a_speaker_diarization', target: '1.3b_asr' },
  { source: '1.3a_speaker_diarization', target: '1.3c_emotion_recognition' },
  { source: '1.2_visual_understanding', target: '2.1_event_structuring' },
  { source: '1.3b_asr', target: '2.1_event_structuring' },
  { source: '1.3c_emotion_recognition', target: '2.1_event_structuring' },
  { source: '2.1_event_structuring', target: '2.2_person_matching' },
  { source: '2.2_person_matching', target: '3.1_profile_update' },
  { source: '3.1_profile_update', target: '3.2_diary_generation' },
  { source: '3.2_diary_generation', target: '4.1_media_slicing' },
  { source: '4.1_media_slicing', target: '4.2_quality_check' },
  { source: '4.2_quality_check', target: '4.3_storage' },
];

// Estimated duration per node (seconds) for progress display
const ESTIMATED_DURATION: Record<string, number> = {
  '1.1_video_preprocess': 5,
  '1.2_visual_understanding': 30,
  '1.3a_speaker_diarization': 3,
  '1.3b_asr': 3,
  '1.3c_emotion_recognition': 3,
  '2.1_event_structuring': 20,
  '2.2_person_matching': 15,
  '3.1_profile_update': 15,
  '3.2_diary_generation': 25,
  '4.1_media_slicing': 5,
  '4.2_quality_check': 15,
  '4.3_storage': 2,
};

const statusColors: Record<string, { bg: string; border: string; dot: string }> = {
  pending: { bg: '#fff', border: '#e5e7eb', dot: '#9ca3af' },
  running: { bg: '#eff6ff', border: '#3b82f6', dot: '#3b82f6' },
  completed: { bg: '#f0fdf4', border: '#22c55e', dot: '#22c55e' },
  failed: { bg: '#fef2f2', border: '#ef4444', dot: '#ef4444' },
  skipped: { bg: '#f9fafb', border: '#d1d5db', dot: '#d1d5db' },
};

function CustomNode({ data, selected }: NodeProps) {
  const colors = statusColors[data.status] || statusColors.pending;
  const isRunning = data.status === 'running';

  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 8,
        border: `2px solid ${selected ? '#3b82f6' : colors.border}`,
        backgroundColor: selected ? '#eff6ff' : colors.bg,
        boxShadow: isRunning ? '0 0 12px rgba(59,130,246,0.3)' : '0 1px 3px rgba(0,0,0,0.1)',
        minWidth: 140,
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#999' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        {isRunning ? (
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            border: '2px solid #93c5fd', borderTopColor: '#3b82f6',
            animation: 'spin 1s linear infinite',
          }} />
        ) : (
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            backgroundColor: colors.dot,
          }} />
        )}
        <span style={{ fontSize: 13, fontWeight: 500 }}>{data.label}</span>
      </div>
      {/* Status line */}
      <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
        {data.status === 'completed' && data.duration != null && `${data.duration.toFixed(1)}s`}
        {data.status === 'running' && `运行中...预计${data.estimate}s`}
        {data.status === 'pending' && data.waitingFor && `等待: ${data.waitingFor}`}
        {data.status === 'failed' && '失败'}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#999' }} />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

// Dependencies for "waiting for" display
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

const NODE_NAMES: Record<string, string> = {};
PIPELINE_NODES.forEach((n) => { NODE_NAMES[n.id] = n.name; });

export default function WorkflowDAG({ nodeRuns, selectedNodeId, onNodeSelect }: WorkflowDAGProps) {
  const nodeRunMap = useMemo(() => {
    const map: Record<string, NodeRunData> = {};
    for (const nr of nodeRuns) {
      map[nr.node_id] = nr;
    }
    return map;
  }, [nodeRuns]);

  // Figure out what pending nodes are waiting for
  const getWaitingFor = (nodeId: string): string => {
    const deps = NODE_DEPS[nodeId] || [];
    const incomplete = deps.filter((d) => {
      const nr = nodeRunMap[d];
      return !nr || nr.status !== 'completed';
    });
    if (incomplete.length === 0) return '';
    return incomplete.map((d) => NODE_NAMES[d] || d).join(', ');
  };

  const nodes: Node[] = PIPELINE_NODES.map((pn) => {
    const nr = nodeRunMap[pn.id];
    return {
      id: pn.id,
      type: 'custom',
      position: { x: pn.x, y: pn.y },
      selected: pn.id === selectedNodeId,
      data: {
        label: pn.name,
        status: nr?.status || 'pending',
        duration: nr?.duration_seconds,
        estimate: ESTIMATED_DURATION[pn.id] || 10,
        waitingFor: getWaitingFor(pn.id),
      },
    };
  });

  const edges: Edge[] = PIPELINE_EDGES.map((pe, i) => {
    const sourceStatus = nodeRunMap[pe.source]?.status;
    const targetStatus = nodeRunMap[pe.target]?.status;
    return {
      id: `e${i}`,
      source: pe.source,
      target: pe.target,
      animated: sourceStatus === 'running' || targetStatus === 'running',
      style: {
        stroke: sourceStatus === 'completed' ? '#22c55e' :
                sourceStatus === 'running' ? '#3b82f6' : '#d1d5db',
        strokeWidth: sourceStatus === 'running' ? 2 : 1,
      },
    };
  });

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onNodeSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
