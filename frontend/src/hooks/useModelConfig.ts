import { useState } from 'react';
import type { ProviderConfig } from '@/types/chat';

interface ModelConfigState {
  current: ProviderConfig;
  pending: ProviderConfig;
}

interface UseModelConfigReturn {
  chatConfig: ModelConfigState;
  embeddingsConfig: ModelConfigState;
  hasChanges: boolean;
  updateChatConfig: (config: ProviderConfig) => void;
  updateEmbeddingsConfig: (config: ProviderConfig) => void;
  confirmChanges: () => void;
  cancelChanges: () => void;
}

export function useModelConfig(
  initialChatConfig: ProviderConfig,
  initialEmbeddingsConfig: ProviderConfig
): UseModelConfigReturn {
  const [chatCurrent, setChatCurrent] = useState(initialChatConfig);
  const [chatPending, setChatPending] = useState(initialChatConfig);
  const [embeddingsCurrent, setEmbeddingsCurrent] = useState(initialEmbeddingsConfig);
  const [embeddingsPending, setEmbeddingsPending] = useState(initialEmbeddingsConfig);

  const hasChanges =
    JSON.stringify(chatPending) !== JSON.stringify(chatCurrent) ||
    JSON.stringify(embeddingsPending) !== JSON.stringify(embeddingsCurrent);

  const confirmChanges = () => {
    setChatCurrent(chatPending);
    setEmbeddingsCurrent(embeddingsPending);
  };

  const cancelChanges = () => {
    setChatPending(chatCurrent);
    setEmbeddingsPending(embeddingsCurrent);
  };

  return {
    chatConfig: { current: chatCurrent, pending: chatPending },
    embeddingsConfig: { current: embeddingsCurrent, pending: embeddingsPending },
    hasChanges,
    updateChatConfig: setChatPending,
    updateEmbeddingsConfig: setEmbeddingsPending,
    confirmChanges,
    cancelChanges,
  };
}
