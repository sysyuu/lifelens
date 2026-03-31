import axios from 'axios';
import { WorkflowRunData, NodeConfigData, AvailableNode } from '../types';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE });

// Default profile ID for V1 (single user)
const PROFILE_ID = process.env.REACT_APP_PROFILE_ID || '';

export function useApi(profileId?: string) {
  const pid = profileId || PROFILE_ID;

  return {
    async listWorkflowRuns(targetDate?: string): Promise<WorkflowRunData[]> {
      const params: Record<string, string> = {};
      if (targetDate) params.target_date = targetDate;
      const res = await api.get(`/api/debug/${pid}/runs`, { params });
      return res.data;
    },

    async listWorkflowDates(): Promise<string[]> {
      const res = await api.get(`/api/debug/${pid}/dates`);
      return res.data;
    },

    async getNodeConfig(nodeId: string): Promise<NodeConfigData> {
      const res = await api.get(`/api/debug/${pid}/config/${nodeId}`);
      return res.data;
    },

    async updateNodeConfig(nodeId: string, data: { model?: string; system_prompt?: string; params?: Record<string, any> }) {
      const res = await api.put(`/api/debug/${pid}/config/${nodeId}`, data);
      return res.data;
    },

    async rerunNode(workflowRunId: string, nodeId: string) {
      const res = await api.post('/api/debug/rerun', {
        workflow_run_id: workflowRunId,
        node_id: nodeId,
      });
      return res.data;
    },

    async listNodes(): Promise<AvailableNode[]> {
      const res = await api.get('/api/debug/nodes');
      return res.data;
    },
  };
}
