import { useEffect, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Message } from '@/types/chat';
import { User, Bot, Loader } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  isStreaming?: boolean;
}

export function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  return (
    <ScrollArea className="flex-1 p-4" ref={scrollRef}>
      <div className="space-y-4 max-w-3xl mx-auto">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-primary-foreground" />
              </div>
            )}
            <div
              className={`rounded-lg px-4 py-2 max-w-[80%] ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/40">
                  <p className="text-xs font-medium text-muted-foreground mb-2">Sources:</p>
                  <div className="space-y-1.5">
                    {message.sources.map((source, index) => (
                      <div key={index} className="flex items-start gap-2 text-xs text-muted-foreground">
                        <span className="flex-shrink-0">📄</span>
                        <div>
                          <span className="font-medium">{source.document_name}</span>
                          <span className="text-muted-foreground/70 ml-1">
                            ({(source.similarity * 100).toFixed(1)}% match)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {message.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-secondary-foreground" />
              </div>
            )}
          </div>
        ))}
        {isStreaming && !streamingContent && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <div className="rounded-lg px-4 py-2 bg-muted">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader className="h-4 w-4 animate-spin" />
                <span className="text-sm">Generating response...</span>
              </div>
            </div>
          </div>
        )}
        {isStreaming && streamingContent && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <div className="rounded-lg px-4 py-2 max-w-[80%] bg-muted">
              <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
              <span className="inline-block w-2 h-4 bg-foreground/50 animate-pulse ml-1" />
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
