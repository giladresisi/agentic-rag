import { useState, useEffect } from 'react';
import { ModelConfigSection } from './ModelConfigSection';
import { Button } from '@/components/ui/button';
import type { ProviderConfig } from '@/types/chat';
import { supabase } from '@/lib/supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  chatConfig: ProviderConfig;
  embeddingsConfig: ProviderConfig;
  onChatConfigChange: (config: ProviderConfig) => void;
  onEmbeddingsConfigChange: (config: ProviderConfig) => void;
  onConfirm: () => void;
  onCancel: () => void;
  hasChanges: boolean;
}

export function SettingsModal({
  isOpen,
  onClose,
  chatConfig,
  embeddingsConfig,
  onChatConfigChange,
  onEmbeddingsConfigChange,
  onConfirm,
  onCancel,
  hasChanges,
}: SettingsModalProps) {
  const [chunksExist, setChunksExist] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const checkChunks = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) return;

        const response = await fetch(`${API_URL}/ingestion/chunks/exists`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setChunksExist(data.exists);
        }
      } catch {
        // Silently fail - default to unlocked
      }
    };

    checkChunks();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleCancel = () => {
    onCancel();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">Settings</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Configure model providers for chat and embeddings
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6 overflow-y-auto">
          <ModelConfigSection
            title="Chat Model"
            description="Model used for chat conversations and LLM completions"
            config={chatConfig}
            onChange={onChatConfigChange}
            isEmbedding={false}
          />

          <div className="border-t" />

          <ModelConfigSection
            title="Embeddings Model"
            description="Model used for document embeddings and vector search"
            config={embeddingsConfig}
            onChange={onEmbeddingsConfigChange}
            isEmbedding={true}
            disabled={chunksExist}
          />
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex justify-end gap-3">
          <Button onClick={handleCancel} variant="outline">
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!hasChanges}>
            Confirm
          </Button>
        </div>
      </div>
    </div>
  );
}
