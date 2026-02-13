export interface Thread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  provider?: string;
  model?: string;
  base_url?: string;
}

export interface Source {
  document_id: string;
  document_name: string;
  chunk_content: string;
  similarity: number;
}

export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources?: Source[];
}

export interface StreamEvent {
  type: 'content_delta' | 'done' | 'error';
  delta?: string;
  error?: string;
}

export interface ProviderConfig {
  provider: string;
  model: string;
  base_url?: string;
}

export interface ProviderPreset {
  name: string;
  base_url: string;
  requires_api_key: boolean;
  models: string[];
}

export interface ProvidersResponse {
  providers: Record<string, ProviderPreset>;
  defaults: {
    provider: string;
    model: string;
    base_url: string;
  };
}
