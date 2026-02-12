export type IngestionStatus = 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  storage_path: string;
  status: IngestionStatus;
  error_message: string | null;
  chunk_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  user_id: string;
  content: string;
  chunk_index: number;
  metadata: Record<string, any> | null;
  created_at: string;
}

export interface UploadDocumentRequest {
  file: File;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  status: IngestionStatus;
  message?: string;
}
