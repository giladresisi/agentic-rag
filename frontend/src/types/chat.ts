export interface Thread {
  id: string;
  title: string;
  openai_thread_id: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface StreamEvent {
  type: 'content_delta' | 'done' | 'error';
  delta?: string;
  error?: string;
}
