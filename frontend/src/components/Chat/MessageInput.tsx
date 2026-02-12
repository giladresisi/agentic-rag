import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Square } from 'lucide-react';

interface MessageInputProps {
  onSendMessage: (content: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
}

export function MessageInput({ onSendMessage, onStop, disabled, isStreaming }: MessageInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleStop = () => {
    if (onStop) {
      onStop();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t p-4">
      <div className="flex gap-2 max-w-3xl mx-auto">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={disabled}
          className="flex-1"
        />
        {isStreaming ? (
          <Button
            type="button"
            onClick={handleStop}
            variant="outline"
            size="icon"
            title="Stop generating"
          >
            <Square className="w-4 h-4" />
          </Button>
        ) : (
          <Button type="submit" disabled={disabled || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        )}
      </div>
    </form>
  );
}
