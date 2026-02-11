import { useState, useEffect } from 'react';
import type { Thread } from '@/types/chat';

const API_URL = import.meta.env.VITE_API_URL;

export function useThreads(token: string | null) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThreads = async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/chat/threads`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch threads');
      }

      const data = await response.json();
      setThreads(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch threads');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, [token]);

  const createThread = async (title: string): Promise<Thread> => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/chat/threads`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error('Failed to create thread');
    }

    const newThread = await response.json();
    setThreads(prev => [newThread, ...prev]);
    return newThread;
  };

  const deleteThread = async (threadId: string) => {
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/chat/threads/${threadId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to delete thread');
    }

    setThreads(prev => prev.filter(t => t.id !== threadId));
  };

  return {
    threads,
    isLoading,
    error,
    createThread,
    deleteThread,
    refreshThreads: fetchThreads,
  };
}
