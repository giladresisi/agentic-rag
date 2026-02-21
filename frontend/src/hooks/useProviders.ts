import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { ProvidersResponse } from '../types/chat';

import { API_URL } from '../lib/api';

export function useProviders() {
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get auth token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      // Fetch providers from backend
      const response = await fetch(`${API_URL}/chat/providers`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch providers');
      }

      const data = await response.json();
      setProviders(data);
    } catch (err) {
      console.error('Error fetching providers:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch providers');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    providers,
    isLoading,
    error,
    refetch: fetchProviders,
  };
}
