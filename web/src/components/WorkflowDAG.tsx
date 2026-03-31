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

const statusColors: Record<string, string> = {
  pending: '#9ca3af',
  running: '#3b82f6',
  completed: '#22c55e',
  failed: '#ef4444',
  skipped: '#d1d5db',
};

function CustomNode({ data, selected }: NodeProps) {
  const statusColor = statusColors[data.status] || '#9ca3af';

  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 8,
        border: selected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
        backgroundColor: selected ? '#eff6ff' : '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        minWidth: 140,
        textAlign: 'center',
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#999' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: statusColor,
          }}
        />
        <span style={{ fontSize: 13, fontWeight: 500 }}>{data.label}</span>
      </div>
      {data.duration && (
        <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
          {data.duration.toFixed(1)}s
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: '#999' }} />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

export default function WorkflowDAG({ nodeRuns, selectedNodeId, onNodeSelect }: WorkflowDAGProps) {
  const nodeRunMap = useMemo(() => {
    const map: Record<string, NodeRunData> = {};
    for (const nr of nodeRuns) {
      map[nr.node_id] = nr;
    }
    return map;
  }, [nodeRuns]);

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
      },
    };
  });

  const edges: Edge[] = PIPELINE_EDGES.map((pe, i) => ({
    id: `e${i}`,
    source: pe.source,
    target: pe.target,
    animated: nodeRunMap[pe.source]?.status === 'running',
    style: { stroke: '#9ca3af' },
  }));

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
    </div>
  );
}
