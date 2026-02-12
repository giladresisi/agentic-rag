import { useState, useEffect } from 'react';
import { useProviders } from '@/hooks/useProviders';
import type { ProviderConfig } from '@/types/chat';
import { Input } from '@/components/ui/input';

interface ModelConfigSectionProps {
  title: string;
  description: string;
  config: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
}

export function ModelConfigSection({ title, description, config, onChange }: ModelConfigSectionProps) {
  const { providers, isLoading } = useProviders();
  const [selectedProvider, setSelectedProvider] = useState(config.provider);
  const [selectedModel, setSelectedModel] = useState(config.model);
  const [customBaseUrl, setCustomBaseUrl] = useState(config.base_url || '');

  useEffect(() => {
    setSelectedProvider(config.provider);
    setSelectedModel(config.model);
    setCustomBaseUrl(config.base_url || '');
  }, [config]);

  useEffect(() => {
    if (providers && selectedProvider) {
      const providerConfig = providers.providers[selectedProvider];
      if (providerConfig?.models.length > 0) {
        setSelectedModel(providerConfig.models[0]);
      }
      if (providerConfig && selectedProvider !== 'custom') {
        setCustomBaseUrl(providerConfig.base_url);
      }
    }
  }, [selectedProvider, providers]);

  useEffect(() => {
    onChange({
      provider: selectedProvider,
      model: selectedModel,
      base_url: customBaseUrl || undefined,
    });
  }, [selectedProvider, selectedModel, customBaseUrl]);

  if (isLoading || !providers) {
    return <div className="text-sm text-muted-foreground">Loading...</div>;
  }

  const currentProviderConfig = providers.providers[selectedProvider];
  const isCustomProvider = selectedProvider === 'custom';

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>

      <div className="space-y-3">
        <div className="space-y-2">
          <label className="text-sm font-medium">Provider</label>
          <select
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
          >
            {Object.entries(providers.providers).map(([key, config]) => (
              <option key={key} value={key}>{config.name}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Model</label>
          {currentProviderConfig.models.length > 0 ? (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
            >
              {currentProviderConfig.models.map((model) => (
                <option key={model} value={model}>{model}</option>
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
      </div>
    </div>
  );
}
