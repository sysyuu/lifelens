export interface NodeRunData {
  id: string;
  node_id: string;
  node_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  model_used: string | null;
  system_prompt: string | null;
  config_params: Record<string, any> | null;
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
  error_message: string | null;
}

export interface WorkflowRunData {
  id: string;
  target_date: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  node_runs: NodeRunData[];
}

export interface NodeConfigData {
  node_id: string;
  defaults: {
    model: string | null;
    system_prompt: string | null;
    params: Record<string, any>;
  };
  overrides: {
    model: string | null;
    system_prompt: string | null;
    params: Record<string, any> | null;
  };
  effective: {
    model: string | null;
    system_prompt: string | null;
    params: Record<string, any>;
  };
}

export interface AvailableNode {
  node_id: string;
  node_name: string;
  default_model: string | null;
  has_system_prompt: boolean;
}
