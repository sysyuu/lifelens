import React, { useState, useEffect, useCallback } from 'react';
import WorkflowDAG from './components/WorkflowDAG';
import NodeDetail from './components/NodeDetail';
import { useApi } from './hooks/useApi';
import { WorkflowRunData, NodeRunData } from './types';
import './App.css';

const PROFILE_ID = process.env.REACT_APP_PROFILE_ID || '';

function App() {
  const api = useApi(PROFILE_ID);
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunData[]>([]);
  const [selectedRunIndex, setSelectedRunIndex] = useState(0);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Load available dates
  useEffect(() => {
    api.listWorkflowDates().then((d) => {
      setDates(d);
      if (d.length > 0) setSelectedDate(d[0]);
    }).catch(console.error);
  }, []);

  // Load runs for selected date
  useEffect(() => {
    if (!selectedDate) return;
    api.listWorkflowRuns(selectedDate).then((runs) => {
      setWorkflowRuns(runs);
      setSelectedRunIndex(0);
    }).catch(console.error);
  }, [selectedDate]);

  const currentRun = workflowRuns[selectedRunIndex] || null;
  const nodeRuns = currentRun?.node_runs || [];
  const selectedNodeRun = nodeRuns.find((nr) => nr.node_id === selectedNodeId) || null;

  const handleRerun = useCallback(() => {
    if (!selectedDate) return;
    api.listWorkflowRuns(selectedDate).then(setWorkflowRuns).catch(console.error);
  }, [selectedDate]);

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
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid #d1d5db',
              fontSize: 13,
            }}
          >
            {dates.length === 0 && <option value="">暂无数据</option>}
            {dates.map((d) => (
              <option key={d} value={d}>
                {d || '未知日期'}
              </option>
            ))}
          </select>
          {workflowRuns.length > 1 && (
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
                {workflowRuns.map((r, i) => (
                  <option key={r.id} value={i}>
                    #{i + 1} - {r.status} ({r.started_at?.slice(11, 19) || 'N/A'})
                  </option>
                ))}
              </select>
            </>
          )}
          {currentRun && (
            <span
              style={{
                fontSize: 12,
                color: currentRun.status === 'completed' ? '#166534' : '#991b1b',
                backgroundColor: currentRun.status === 'completed' ? '#dcfce7' : '#fef2f2',
                padding: '3px 10px',
                borderRadius: 12,
              }}
            >
              {currentRun.status}
            </span>
          )}
        </div>
      </header>

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
            />
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#9ca3af',
                fontSize: 14,
              }}
            >
              点击左侧节点查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
