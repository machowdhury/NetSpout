import { useCallback, useEffect, useState } from 'react';
import { fetchJson } from '../lib/api';
import type {
  CatalogEvidence,
  CatalogIntegration,
  CatalogSource,
  CatalogSummary,
} from '../types/catalog';

export interface CatalogData {
  sources: CatalogSource[];
  integrations: CatalogIntegration[];
  evidence: CatalogEvidence[];
  summary: CatalogSummary;
}

interface CatalogDataState {
  data: CatalogData | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

export function useCatalogData(): CatalogDataState {
  const [data, setData] = useState<CatalogData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRequestVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    let active = true;

    Promise.all([
      fetchJson<CatalogSource[]>('/api/catalog/sources'),
      fetchJson<CatalogIntegration[]>('/api/catalog/integrations'),
      fetchJson<CatalogEvidence[]>('/api/catalog/evidence'),
      fetchJson<CatalogSummary>('/api/catalog/summary'),
    ])
      .then(([sources, integrations, evidence, summary]) => {
        if (!active) return;
        setData({ sources, integrations, evidence, summary });
        setLoading(false);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setData(null);
        setLoading(false);
        setError(reason instanceof Error ? reason.message : 'Unknown catalog error');
      });

    return () => {
      active = false;
    };
  }, [requestVersion]);

  return { data, loading, error, retry };
}
