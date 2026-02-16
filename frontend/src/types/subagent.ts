export interface ReasoningStep {
  step_number: number;
  content: string;
  timestamp: string;
}

export interface SubAgentMetadata {
  task_description: string;
  document_id: string;
  document_name: string;
  status: 'completed' | 'failed' | 'processing';
  reasoning_steps: ReasoningStep[];
  result?: string;
  error?: string;
}
