import { fetchJson } from './api';
import type {
  DashboardCatalog,
  DashboardPack,
  DashboardStudioExport,
} from '../types/dashboard';

const parameters = (runId?: string, index?: string) => {
  const result = new URLSearchParams();
  if (runId) result.set('run_id', runId);
  if (index) result.set('index', index);
  const encoded = result.toString();
  return encoded ? `?${encoded}` : '';
};

export const dashboardApi = {
  catalog: () => fetchJson<DashboardCatalog>('/api/dashboards'),
  pack: (dashboardId: string, runId?: string, index?: string) =>
    fetchJson<DashboardPack>(
      `/api/dashboards/${encodeURIComponent(dashboardId)}${parameters(runId, index)}`,
    ),
  export: (dashboardId: string, runId?: string, index?: string) =>
    fetchJson<DashboardStudioExport>(
      `/api/dashboards/${encodeURIComponent(dashboardId)}/export${parameters(runId, index)}`,
    ),
};
