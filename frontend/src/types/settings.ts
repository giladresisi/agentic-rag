import type { ProviderConfig } from './chat';

export interface ModelSettings {
  chat: ProviderConfig;
  embeddings: ProviderConfig;
}
