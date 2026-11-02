import { fetchJson } from './api';
import type { Cisco100Catalog } from '../types/cisco100';
import type { StudioScenarioPack } from '../types/studio';

export const cisco100Api = {
  catalog: () => fetchJson<Cisco100Catalog>('/api/cisco100'),
  studioDraft: (scenarioId: string) =>
    fetchJson<StudioScenarioPack>(`/api/cisco100/scenarios/${scenarioId}/studio-draft`, {
      method: 'POST',
    }),
};
