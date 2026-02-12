import { useState, useEffect } from 'react';
import { useProviders } from '../../hooks/useProviders';
import type { ProviderConfig } from '../../types/chat';
import { Card } from '../ui/card';
import { Input } from '../ui/input';

interface ProviderSelectorProps {
  value: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
}

export function ProviderSelector({ value, onChange }: ProviderSelectorProps) {
  const { providers, isLoading } = useProviders();
  const [selectedProvider, setSelectedProvider] = useState(value.provider);
  const [selectedModel, setSelectedModel] = useState(value.model);
  const [customBaseUrl, setCustomBaseUrl] = useState(value.base_url || '');
  const [customApiKey, setCustomApiKey] = useState(value.api_key || '');

  // Update parent when values change
  useEffect(() => {
    onChange({
      provider: selectedProvider,
      model: selectedModel,
      base_url: customBaseUrl || undefined,
      api_key: customApiKey || undefined,
    });
  }, [selectedProvider, selectedModel, customBaseUrl, customApiKey]);

  // Update model when provider changes
  useEffect(() => {
    if (providers && selectedProvider) {
      const providerConfig = providers.providers[selectedProvider];
      if (providerConfig && providerConfig.models.length > 0) {
        setSelectedModel(providerConfig.models[0]);
      }
      // Set base_url from provider preset
      if (providerConfig && selectedProvider !== 'custom') {
        setCustomBaseUrl(providerConfig.base_url);
      }
    }
  }, [selectedProvider, providers]);

  if (isLoading || !providers) {
    return (
      <Card className="p-4">
        <div className="text-sm text-muted-foreground">Loading providers...</div>
      </Card>
    );
  }

  const currentProviderConfig = providers.providers[selectedProvider];
  const isCustomProvider = selectedProvider === 'custom';
  const requiresApiKey = currentProviderConfig?.requires_api_key;

  return (
    <Card className="p-4 space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Provider</label>
        <select
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
        >
          {Object.entries(providers.providers).map(([key, config]) => (
            <option key={key} value={key}>
              {config.name}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Model</label>
        {currentProviderConfig.models.length > 0 ? (
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {currentProviderConfig.models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        ) : (
          <Input
            type="text"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            placeholder="Enter model name"
          />
        )}
      </div>

      {isCustomProvider && (
        <div className="space-y-2">
          <label className="text-sm font-medium">Base URL</label>
          <Input
            type="text"
            value={customBaseUrl}
            onChange={(e) => setCustomBaseUrl(e.target.value)}
            placeholder="https://api.example.com/v1"
          />
        </div>
      )}

      {requiresApiKey && (
        <div className="space-y-2">
          <label className="text-sm font-medium">
            API Key
            {!isCustomProvider && (
              <span className="text-xs text-muted-foreground ml-2">
                (Optional - uses default if not provided)
              </span>
            )}
          </label>
          <Input
            type="password"
            value={customApiKey}
            onChange={(e) => setCustomApiKey(e.target.value)}
            placeholder="sk-..."
          />
        </div>
      )}

      <div className="text-xs text-muted-foreground">
        {currentProviderConfig.requires_api_key && !customApiKey && !isCustomProvider && (
          <p>Using default API key from server configuration</p>
        )}
        {selectedProvider === 'ollama' && (
          <p>Make sure Ollama is running locally on port 11434</p>
        )}
        {selectedProvider === 'lmstudio' && (
          <p>Make sure LM Studio server is running on port 1234</p>
        )}
      </div>
    </Card>
  );
}
