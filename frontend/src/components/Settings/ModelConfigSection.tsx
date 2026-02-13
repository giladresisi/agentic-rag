import { useState, useEffect, useRef, useCallback } from 'react';
import { useProviders } from '@/hooks/useProviders';
import type { ProviderConfig } from '@/types/chat';
import { Input } from '@/components/ui/input';

interface ModelConfigSectionProps {
  title: string;
  description: string;
  config: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
  isEmbedding?: boolean;
  disabled?: boolean;
}

export function ModelConfigSection({
  title,
  description,
  config,
  onChange,
  isEmbedding = false,
  disabled = false,
}: ModelConfigSectionProps) {
  const { providers, isLoading } = useProviders();
  const [selectedProvider, setSelectedProvider] = useState(config.provider);
  const [selectedModel, setSelectedModel] = useState(config.model);
  const [customBaseUrl, setCustomBaseUrl] = useState(config.base_url || '');
  const [dimensions, setDimensions] = useState(config.dimensions || 1536);
  const isInitialMount = useRef(true);
  const lastSentConfig = useRef<string>('');
  const ignoreNextConfigUpdate = useRef(false);

  useEffect(() => {
    // Skip updates that came from our own onChange calls
    if (ignoreNextConfigUpdate.current) {
      ignoreNextConfigUpdate.current = false;
      return;
    }

    setSelectedProvider(config.provider);
    setSelectedModel(config.model);
    setCustomBaseUrl(config.base_url || '');
    setDimensions(config.dimensions || 1536);
  }, [config]);

  // When provider changes, auto-select first model and update base URL
  useEffect(() => {
    if (isInitialMount.current) return;

    if (providers && selectedProvider) {
      const providerConfig = providers.providers[selectedProvider];
      if (!providerConfig) return;

      if (isEmbedding) {
        // For embeddings, select first embedding model if available
        if (providerConfig.embedding_models.length > 0) {
          const firstEmbedding = providerConfig.embedding_models[0];
          setSelectedModel(firstEmbedding.name);
          setDimensions(firstEmbedding.dimensions);
        }
        // If no models available (LM Studio), keep current model
      } else {
        // For chat, select first chat model if available
        if (providerConfig.chat_models.length > 0) {
          setSelectedModel(providerConfig.chat_models[0]);
        }
        // If no models available (LM Studio), keep current model
      }

      // Auto-populate base URL for OpenAI/OpenRouter, clear for LM Studio
      if (selectedProvider === 'lmstudio') {
        setCustomBaseUrl('');
      } else if (providerConfig.base_url) {
        setCustomBaseUrl(providerConfig.base_url);
      }
    }
  }, [selectedProvider, providers, isEmbedding]);

  // Notify parent of changes - wrapped to avoid dependency issues
  const notifyChange = useCallback(() => {
    const updatedConfig: ProviderConfig = {
      provider: selectedProvider,
      model: selectedModel,
      base_url: customBaseUrl || undefined,
    };

    if (isEmbedding) {
      updatedConfig.dimensions = dimensions;
    }

    // Prevent infinite loops by only calling onChange if config actually changed
    const configKey = JSON.stringify(updatedConfig);
    if (configKey !== lastSentConfig.current) {
      lastSentConfig.current = configKey;
      ignoreNextConfigUpdate.current = true;
      onChange(updatedConfig);
    }
  }, [selectedProvider, selectedModel, customBaseUrl, dimensions, isEmbedding, onChange]);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    notifyChange();
  }, [notifyChange]);

  if (isLoading || !providers) {
    return <div className="text-sm text-muted-foreground">Loading...</div>;
  }

  const currentProviderConfig = providers.providers[selectedProvider];
  const isLmStudio = selectedProvider === 'lmstudio';
  const isOpenAI = selectedProvider === 'openai';

  // Determine which models to show based on isEmbedding
  const modelList = isEmbedding
    ? currentProviderConfig?.embedding_models.map((m) => m.name) || []
    : currentProviderConfig?.chat_models || [];

  // For OpenAI embeddings, show dimensions in the dropdown label
  const embeddingModelsMap = isEmbedding && isOpenAI && currentProviderConfig
    ? Object.fromEntries(currentProviderConfig.embedding_models.map((m) => [m.name, m.dimensions]))
    : {};

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    // If OpenAI embedding, update dimensions from the model info
    if (isEmbedding && isOpenAI && currentProviderConfig) {
      const embeddingModel = currentProviderConfig.embedding_models.find((m) => m.name === model);
      if (embeddingModel) {
        setDimensions(embeddingModel.dimensions);
      }
    }
  };

  return (
    <div className={`space-y-4 ${disabled ? 'opacity-60' : ''}`}>
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>

      {disabled && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-md">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">
            Cannot change embedding model while documents exist. Delete all documents first.
          </p>
        </div>
      )}

      <div className="space-y-3">
        <div className="space-y-2">
          <label className="text-sm font-medium">Provider</label>
          <select
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            disabled={disabled}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm disabled:cursor-not-allowed"
          >
            {Object.entries(providers.providers).map(([key, config]) => (
              <option key={key} value={key}>{config.name}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Model</label>
          {modelList.length > 0 ? (
            <select
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
              disabled={disabled}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm disabled:cursor-not-allowed"
            >
              {modelList.map((model) => (
                <option key={model} value={model}>
                  {isEmbedding && embeddingModelsMap[model]
                    ? `${model} (${embeddingModelsMap[model]} dims)`
                    : model}
                </option>
              ))}
            </select>
          ) : (
            <Input
              type="text"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="Enter model name"
              disabled={disabled}
            />
          )}
        </div>

        {/* Dimensions input for OpenRouter/LM Studio embeddings */}
        {isEmbedding && !isOpenAI && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Dimensions</label>
            <Input
              type="number"
              value={dimensions}
              onChange={(e) => setDimensions(parseInt(e.target.value) || 1536)}
              placeholder="1536"
              disabled={disabled}
            />
          </div>
        )}

        {/* Base URL: always shown for LM Studio, hidden for others */}
        {isLmStudio && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Base URL</label>
            <Input
              type="text"
              value={customBaseUrl}
              onChange={(e) => setCustomBaseUrl(e.target.value)}
              placeholder="http://localhost:1234/v1"
              disabled={disabled}
            />
          </div>
        )}
      </div>
    </div>
  );
}
