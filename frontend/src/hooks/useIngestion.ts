import { useState, useEffect } from 'react';
import type { Document, Chunk } from '@/types/ingestion';
import { supabase } from '@/lib/supabase';

const API_URL = import.meta.env.VITE_API_URL || '';

export function useIngestion(token: string | null) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
          console.log('[REALTIME] Received update:', payload.eventType, payload.new);

          // Handle INSERT
          if (payload.eventType === 'INSERT') {
            setDocuments((prev) => [payload.new as Document, ...prev]);
          }
          // Handle UPDATE
          else if (payload.eventType === 'UPDATE') {
            console.log('[REALTIME] Updating document:', payload.new.id, 'to status:', payload.new.status);
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
      .subscribe((status) => {
        console.log('[REALTIME] Subscription status:', status);
      });

    return () => {
      channel.unsubscribe();
    };
  }, [token]);

  const uploadDocument = async (file: File): Promise<void> => {
    if (!token) throw new Error('Not authenticated');

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/ingestion/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          console.error('[UPLOAD ERROR]', errorData);
          throw new Error(errorData.detail || 'Failed to upload document');
        } else {
          throw new Error(`API error: ${response.status} ${response.statusText}. Make sure the backend server is running at ${API_URL || 'http://localhost:8000'}`);
        }
      }

      // Document will be added via Realtime subscription
      // Refresh to ensure consistency
      await fetchDocuments();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload document';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
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
