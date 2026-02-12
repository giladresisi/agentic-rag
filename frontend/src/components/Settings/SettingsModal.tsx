import { ModelConfigSection } from './ModelConfigSection';
import { Button } from '@/components/ui/button';
import type { ProviderConfig } from '@/types/chat';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  chatConfig: ProviderConfig;
  embeddingsConfig: ProviderConfig;
  onChatConfigChange: (config: ProviderConfig) => void;
  onEmbeddingsConfigChange: (config: ProviderConfig) => void;
  onConfirm: () => void;
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
  hasChanges,
}: SettingsModalProps) {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleCancel = () => {
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
          />

          <div className="border-t" />

          <ModelConfigSection
            title="Embeddings Model"
            description="Model used for document embeddings and vector search"
            config={embeddingsConfig}
            onChange={onEmbeddingsConfigChange}
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
