import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useThreads } from '@/hooks/useThreads';
import { useChat } from '@/hooks/useChat';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { Button } from '@/components/ui/button';
import { LogOut } from 'lucide-react';

export function ChatInterface() {
  const { user, token, logout } = useAuth();
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);

  const { threads, createThread, deleteThread } = useThreads(token);
  const {
    messages,
    isStreaming,
    streamingContent,
    sendMessage,
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
      await sendMessage(content);
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
      />
      <div className="flex-1 flex flex-col">
        <header className="border-b p-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold">
            {currentThreadId
              ? threads.find(t => t.id === currentThreadId)?.title || 'Chat'
              : 'Agentic RAG Masterclass'}
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
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
              disabled={isStreaming}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <p>Select a thread or create a new one to start chatting</p>
          </div>
        )}
      </div>
    </div>
  );
}
