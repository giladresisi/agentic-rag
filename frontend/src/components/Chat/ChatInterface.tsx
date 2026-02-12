import { useState, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useThreads } from '@/hooks/useThreads';
import { useChat } from '@/hooks/useChat';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { SettingsModal } from '@/components/Settings/SettingsModal';
import { useModelConfig } from '@/hooks/useModelConfig';

export function ChatInterface() {
  const { user, token, logout } = useAuth();
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const modelConfig = useModelConfig(
    { provider: 'openai', model: 'gpt-4o-mini' },
    { provider: 'openai', model: 'text-embedding-3-small' }
  );
  const [showSettings, setShowSettings] = useState(false);
  const titleGeneratedForThreads = useRef<Set<string>>(new Set());

  const { threads, createThread, deleteThread, generateThreadTitle } = useThreads(token);
  const {
    messages,
    isStreaming,
    streamingContent,
    sendMessage,
    stopMessage,
  } = useChat(currentThreadId, token);

  const handleCreateThread = async () => {
    try {
      const newThread = await createThread('New Chat');
      setCurrentThreadId(newThread.id);
    } catch (error) {
      console.error('Failed to create thread:', error);
    }
  };

  const handleDeleteThread = async (threadId: string) => {
    try {
      await deleteThread(threadId);
      if (currentThreadId === threadId) {
        setCurrentThreadId(null);
      }
    } catch (error) {
      console.error('Failed to delete thread:', error);
    }
  };

  const handleSendMessage = async (content: string) => {
    try {
      await sendMessage(content, modelConfig.chatConfig.current);

      // Generate title for thread after first message (non-blocking)
      if (currentThreadId && !titleGeneratedForThreads.current.has(currentThreadId)) {
        const currentThread = threads.find(t => t.id === currentThreadId);
        if (currentThread && currentThread.title === 'New Chat') {
          // Fire off title generation in the background without awaiting
          generateThreadTitle(currentThreadId)
            .then(() => {
              titleGeneratedForThreads.current.add(currentThreadId);
            })
            .catch((error) => {
              console.error('Failed to generate thread title:', error);
              // Silently fail - not critical to the user experience
            });
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className="flex h-screen">
      <ThreadSidebar
        threads={threads}
        currentThreadId={currentThreadId}
        onSelectThread={setCurrentThreadId}
        onCreateThread={handleCreateThread}
        onDeleteThread={handleDeleteThread}
        user={user}
        onSettingsClick={() => setShowSettings(true)}
        onLogout={logout}
      />
      <div className="flex-1 flex flex-col">
        <header className="border-b p-4">
          <h1 className="text-xl font-semibold">
            {currentThreadId
              ? threads.find(t => t.id === currentThreadId)?.title || 'Chat'
              : 'Agentic RAG Masterclass'}
          </h1>
        </header>
        {currentThreadId ? (
          <>
            <MessageList
              messages={messages}
              streamingContent={streamingContent}
              isStreaming={isStreaming}
            />
            <MessageInput
              onSendMessage={handleSendMessage}
              onStop={stopMessage}
              disabled={isStreaming}
              isStreaming={isStreaming}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <p>Select a thread or create a new one to start chatting</p>
          </div>
        )}
      </div>
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        chatConfig={modelConfig.chatConfig.pending}
        embeddingsConfig={modelConfig.embeddingsConfig.pending}
        onChatConfigChange={modelConfig.updateChatConfig}
        onEmbeddingsConfigChange={modelConfig.updateEmbeddingsConfig}
        onConfirm={modelConfig.confirmChanges}
        hasChanges={modelConfig.hasChanges}
      />
    </div>
  );
}
