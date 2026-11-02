import { fetchJson } from './api';
import type { CiscoCoverageCatalog } from '../types/coverage';

export const coverageApi = {
  cisco: () => fetchJson<CiscoCoverageCatalog>('/api/coverage/cisco'),
};
