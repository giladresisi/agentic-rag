import { useState, useEffect, useRef } from 'react';
import type { Document, Chunk } from '@/types/ingestion';
import type { ProviderConfig } from '@/types/chat';
import { supabase } from '@/lib/supabase';

import { API_URL } from '@/lib/api';

export function useIngestion(token: string | null) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track pending upload request to prevent duplicates
  const pendingUploadRef = useRef<AbortController | null>(null);

  const fetchDocuments = async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/ingestion/documents`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch documents');
        } else {
          throw new Error(`API error: ${response.status} ${response.statusText}. Make sure the backend server is running at ${API_URL || 'http://localhost:8000'}`);
        }
      }

      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      if (err instanceof Error && err.message.includes('<!doctype')) {
        setError(`Backend API not available. Make sure the server is running at ${API_URL || 'http://localhost:8000'}`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch documents');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();

    // Subscribe to Realtime updates on documents table
    if (!token) return;

    const channel = supabase
      .channel('document-updates')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'documents',
        },
        (payload) => {
          // Handle INSERT
          if (payload.eventType === 'INSERT') {
            setDocuments((prev) => [payload.new as Document, ...prev]);
          }
          // Handle UPDATE
          else if (payload.eventType === 'UPDATE') {
            setDocuments((prev) =>
              prev.map((doc) =>
                doc.id === payload.new.id ? (payload.new as Document) : doc
              )
            );
          }
          // Handle DELETE
          else if (payload.eventType === 'DELETE') {
            setDocuments((prev) =>
              prev.filter((doc) => doc.id !== payload.old.id)
            );
          }
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [token]);

  const uploadDocument = async (file: File, embeddingConfig?: ProviderConfig): Promise<void> => {
    if (!token) throw new Error('Not authenticated');

    // Cancel any pending upload request (prevents duplicates from React Strict Mode)
    if (pendingUploadRef.current) {
      pendingUploadRef.current.abort();
    }

    // Create new AbortController for this upload
    const controller = new AbortController();
    pendingUploadRef.current = controller;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      if (embeddingConfig) {
        formData.append('provider', embeddingConfig.provider);
        formData.append('model', embeddingConfig.model);
        if (embeddingConfig.dimensions) {
          formData.append('dimensions', String(embeddingConfig.dimensions));
        }
        if (embeddingConfig.base_url) {
          formData.append('base_url', embeddingConfig.base_url);
        }
      }

      const response = await fetch(`${API_URL}/ingestion/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to upload document');
        } else {
          throw new Error(`API error: ${response.status} ${response.statusText}. Make sure the backend server is running at ${API_URL || 'http://localhost:8000'}`);
        }
      }

      // Document will be added via Realtime subscription
      // Refresh to ensure consistency
      await fetchDocuments();
    } catch (err) {
      // Don't treat aborted requests as errors (expected when canceling duplicates)
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to upload document';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      // Clear pending request reference
      pendingUploadRef.current = null;
      setIsUploading(false);
    }
  };

  const deleteDocument = async (documentId: string): Promise<void> => {
    if (!token) throw new Error('Not authenticated');

    try {
      const response = await fetch(
        `${API_URL}/ingestion/documents/${documentId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete document');
      }

      // Document will be removed via Realtime subscription
      // Refresh to ensure consistency
      await fetchDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
      throw err;
    }
  };

  const fetchChunks = async (documentId: string): Promise<Chunk[]> => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(
      `${API_URL}/ingestion/documents/${documentId}/chunks`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch chunks');
    }

    return response.json();
  };

  return {
    documents,
    isLoading,
    isUploading,
    error,
    uploadDocument,
    deleteDocument,
    fetchChunks,
    refreshDocuments: fetchDocuments,
  };
}
