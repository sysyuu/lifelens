import React, { useState, useEffect, useCallback, useRef } from 'react';
import WorkflowDAG from './components/WorkflowDAG';
import NodeDetail from './components/NodeDetail';
import { useApi } from './hooks/useApi';
import { WorkflowRunData, NodeRunData } from './types';
import './App.css';

const PROFILE_ID = process.env.REACT_APP_PROFILE_ID || '863cdd18-82cb-4ce4-84ed-b74db1a98416';
const POLL_FAST = 2000;
const POLL_SLOW = 5000;

function App() {
  const api = useApi(PROFILE_ID);
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('__all__');
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunData[]>([]);
  const [selectedRunIndex, setSelectedRunIndex] = useState(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const prevRunCountRef = useRef(0);

  // Refresh dates list
  const refreshDates = useCallback(async () => {
    try {
      const d = await api.listWorkflowDates();
      setDates(d);
    } catch {}
  }, []);

  // Load runs — when "__all__" is selected, fetch without date filter to get ALL runs
  const loadRuns = useCallback(async () => {
    try {
      const dateParam = (selectedDate === '__all__' || selectedDate === '__null__') ? undefined : selectedDate;
      const runs = await api.listWorkflowRuns(dateParam);
      setWorkflowRuns((prev) => {
        if (JSON.stringify(prev) !== JSON.stringify(runs)) {
          // Auto-select the latest run if new runs appeared
          if (runs.length > prev.length) {
            setSelectedRunIndex(0); // runs are sorted desc by started_at
          }
          return runs;
        }
        return prev;
      });
    } catch (e) {
      console.error(e);
    }
  }, [selectedDate]);

  // Initial load
  useEffect(() => {
    refreshDates();
    loadRuns();
  }, []);

  // Reload when date filter changes
  useEffect(() => {
    loadRuns();
  }, [selectedDate]);

  // Unified polling
  useEffect(() => {
    const currentRun = workflowRuns[selectedRunIndex];
    const isRunning = currentRun?.status === 'running' ||
      currentRun?.node_runs?.some((nr) => nr.status === 'running');

    const interval = isRunning ? POLL_FAST : POLL_SLOW;

    pollRef.current = setInterval(() => {
      loadRuns();
      if (!isRunning) refreshDates();
    }, interval);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [workflowRuns, selectedRunIndex, loadRuns, refreshDates]);

  const currentRun = workflowRuns[selectedRunIndex] || null;
  const nodeRuns = currentRun?.node_runs || [];
  const selectedNodeRun = nodeRuns.find((nr) => nr.node_id === selectedNodeId) || null;

  // Calculate overall progress
  const completedCount = nodeRuns.filter((nr) => nr.status === 'completed').length;
  const totalNodes = 12;
  const progressPct = totalNodes > 0 ? Math.round((completedCount / totalNodes) * 100) : 0;
  const runningNode = nodeRuns.find((nr) => nr.status === 'running');

  const handleRerun = useCallback(() => {
    loadRuns();
  }, [loadRuns]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: '-apple-system, sans-serif' }}>
      {/* Top bar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px',
          borderBottom: '1px solid #e5e7eb',
          backgroundColor: '#fff',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
          LifeLens 工作流调试面板
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ fontSize: 13, color: '#6b7280' }}>日期：</label>
          <select
            value={selectedDate}
            onChange={(e) => { setSelectedDate(e.target.value); setSelectedRunIndex(0); }}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid #d1d5db',
              fontSize: 13,
            }}
          >
            <option value="__all__">全部</option>
            {dates.map((d) => (
              <option key={d || 'null'} value={d || '__null__'}>
                {d || '未知日期'}
              </option>
            ))}
          </select>
          {workflowRuns.length > 0 && (
            <>
              <label style={{ fontSize: 13, color: '#6b7280' }}>运行：</label>
              <select
                value={selectedRunIndex}
                onChange={(e) => setSelectedRunIndex(Number(e.target.value))}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  border: '1px solid #d1d5db',
                  fontSize: 13,
                }}
              >
                {workflowRuns.map((r, i) => {
                  const videoCount = r.node_runs?.find(nr => nr.node_id === '1.1_video_preprocess')
                    ?.input_data?.video_paths?.length;
                  const dateLabel = r.target_date || '未知日期';
                  const timeLabel = r.started_at?.slice(5, 16).replace('T', ' ') || 'N/A';
                  const statusLabel = r.status === 'running' ? '运行中' :
                                     r.status === 'completed' ? '已完成' :
                                     r.status === 'failed' ? '失败' : r.status;
                  return (
                    <option key={r.id} value={i}>
                      #{workflowRuns.length - i} {timeLabel} [{statusLabel}]{videoCount ? ` ${videoCount}个视频` : ''} ({dateLabel})
                    </option>
                  );
                })}
              </select>
            </>
          )}
          {currentRun && (
            <span
              style={{
                fontSize: 12,
                color: currentRun.status === 'completed' ? '#166534' :
                       currentRun.status === 'running' ? '#1e40af' : '#991b1b',
                backgroundColor: currentRun.status === 'completed' ? '#dcfce7' :
                                 currentRun.status === 'running' ? '#dbeafe' : '#fef2f2',
                padding: '3px 10px',
                borderRadius: 12,
              }}
            >
              {currentRun.status === 'running' ? `处理中 ${progressPct}%` : currentRun.status}
            </span>
          )}
        </div>
      </header>

      {/* Progress bar when running */}
      {currentRun?.status === 'running' && (
        <div style={{ height: 3, backgroundColor: '#e5e7eb' }}>
          <div
            style={{
              height: '100%',
              width: `${progressPct}%`,
              backgroundColor: '#3b82f6',
              transition: 'width 0.5s ease',
            }}
          />
        </div>
      )}

      {/* Running status banner */}
      {runningNode && (
        <div
          style={{
            padding: '8px 20px',
            backgroundColor: '#eff6ff',
            borderBottom: '1px solid #bfdbfe',
            fontSize: 13,
            color: '#1e40af',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span className="spinner" style={{
            display: 'inline-block',
            width: 14,
            height: 14,
            border: '2px solid #93c5fd',
            borderTopColor: '#3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          正在执行：{runningNode.node_name}（{completedCount}/{totalNodes} 节点已完成）
          {runningNode.started_at && (
            <span style={{ color: '#6b7280', marginLeft: 8 }}>
              已运行 {getElapsed(runningNode.started_at)}
            </span>
          )}
        </div>
      )}

      {/* Main content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: DAG */}
        <div style={{ flex: 1, borderRight: '1px solid #e5e7eb' }}>
          <WorkflowDAG
            nodeRuns={nodeRuns}
            selectedNodeId={selectedNodeId}
            onNodeSelect={setSelectedNodeId}
          />
        </div>

        {/* Right: Node detail */}
        <div style={{ width: 480, backgroundColor: '#fff', overflow: 'auto' }}>
          {selectedNodeId ? (
            <NodeDetail
              nodeRun={selectedNodeRun}
              nodeId={selectedNodeId}
              workflowRunId={currentRun?.id || null}
              profileId={PROFILE_ID}
              onRerun={handleRerun}
              allNodeRuns={nodeRuns}
            />
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#9ca3af',
                fontSize: 14,
                gap: 8,
              }}
            >
              <span>点击左侧节点查看详情</span>
              {currentRun && (
                <span style={{ fontSize: 12 }}>
                  {completedCount}/{totalNodes} 节点已完成
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function getElapsed(startedAt: string): string {
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  const seconds = Math.floor((now - start) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m${secs}s`;
}

export default App;
