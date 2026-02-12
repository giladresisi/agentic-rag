import { useState, useEffect, useRef } from 'react';
import type { Message, ProviderConfig } from '@/types/chat';

const API_URL = import.meta.env.VITE_API_URL || '';

export function useChat(threadId: string | null, token: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchMessages = async () => {
    if (!threadId || !token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/chat/threads/${threadId}/messages`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch messages');
      }

      const data = await response.json();
      setMessages(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch messages');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Cancel any in-flight streaming when thread changes
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setStreamingContent('');
    fetchMessages();
  }, [threadId, token]);

  const sendMessage = async (content: string, providerConfig?: ProviderConfig) => {
    if (!threadId || !token) throw new Error('Not authenticated or no thread selected');

    // Capture the current thread ID to validate later
    const currentThreadId = threadId;

    setIsStreaming(true);
    setStreamingContent('');
    setError(null);

    // Add user message to UI immediately
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      thread_id: currentThreadId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Create abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      // Build request body with provider config
      const requestBody: any = { content };
      if (providerConfig) {
        requestBody.provider = providerConfig.provider;
        requestBody.model = providerConfig.model;
        if (providerConfig.base_url) {
          requestBody.base_url = providerConfig.base_url;
        }
      }

      const response = await fetch(
        `${API_URL}/chat/threads/${currentThreadId}/messages`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify(requestBody),
          signal: abortController.signal,
        }
      );

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response stream');
      }

      let fullResponse = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();

            if (data === '[DONE]') {
              // Only add message if we're still on the same thread
              if (currentThreadId === threadId) {
                const assistantMessage: Message = {
                  id: `temp-${Date.now()}-assistant`,
                  thread_id: currentThreadId,
                  role: 'assistant',
                  content: fullResponse,
                  created_at: new Date().toISOString(),
                };
                setMessages(prev => [...prev, assistantMessage]);
                setStreamingContent('');
              }
              setIsStreaming(false);
              abortControllerRef.current = null;
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'content_delta' && parsed.delta) {
                fullResponse += parsed.delta;
                // Only update streaming content if still on same thread
                if (currentThreadId === threadId) {
                  setStreamingContent(fullResponse);
                }
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      // Stream ended without [DONE] - add the final message if on same thread
      if (fullResponse && currentThreadId === threadId) {
        const assistantMessage: Message = {
          id: `temp-${Date.now()}-assistant`,
          thread_id: currentThreadId,
          role: 'assistant',
          content: fullResponse,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
      setStreamingContent('');
      setIsStreaming(false);
      abortControllerRef.current = null;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was aborted - reset state and allow new messages
        setIsStreaming(false);
        setStreamingContent('');
        abortControllerRef.current = null;
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to send message');
      setIsStreaming(false);
      setStreamingContent('');
      abortControllerRef.current = null;
    }
  };

  const stopMessage = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return {
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    error,
    sendMessage,
    stopMessage,
    refreshMessages: fetchMessages,
  };
}
