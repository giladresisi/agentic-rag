import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Thread } from '@/types/chat';
import { Plus, MessageSquare, Trash2, FileText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { UserProfileMenu } from '@/components/Layout/UserProfileMenu';

interface ThreadSidebarProps {
  threads: Thread[];
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  user: { email: string } | null;
  onSettingsClick: () => void;
  onLogout: () => void;
}

export function ThreadSidebar({
  threads,
  currentThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  user,
  onSettingsClick,
  onLogout,
}: ThreadSidebarProps) {
  const location = useLocation();
  const isChat = location.pathname === '/chat';

  return (
    <div className="w-64 border-r bg-muted/10 flex flex-col h-full">
      {/* Mode Toggle */}
      <div className="p-4 border-b">
        <div className="grid grid-cols-2 gap-2">
          <Link to="/chat" className="w-full">
            <Button
              variant={isChat ? 'default' : 'outline'}
              size="sm"
              className="w-full"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Chat
            </Button>
          </Link>
          <Link to="/ingestion" className="w-full">
            <Button
              variant={!isChat ? 'default' : 'outline'}
              size="sm"
              className="w-full"
            >
              <FileText className="w-4 h-4 mr-2" />
              Documents
            </Button>
          </Link>
        </div>
      </div>

      {/* New Thread Button */}
      <div className="p-4 border-b">
        <Button onClick={onCreateThread} className="w-full" size="sm">
          <Plus className="w-4 h-4 mr-2" />
          New Thread
        </Button>
      </div>

      {/* Thread List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {threads.map((thread) => (
            <div
              key={thread.id}
              className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                currentThreadId === thread.id
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              }`}
              onClick={() => onSelectThread(thread.id)}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm truncate">{thread.title}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className={`h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity ${
                  currentThreadId === thread.id ? 'text-primary-foreground' : ''
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteThread(thread.id);
                }}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* User profile at bottom */}
      <div className="border-t">
        <UserProfileMenu
          user={user}
          onSettingsClick={onSettingsClick}
          onLogout={onLogout}
        />
      </div>
    </div>
  );
}
