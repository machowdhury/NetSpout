export type DomainId =
  | 'netops'
  | 'secops'
  | 'itops'
  | 'observability'
  | 'agentic-ai'
  | 'supply-chain';

export type ExperienceMode = 'simple' | 'advanced';

export type ProductMaturity =
  | 'AVAILABLE'
  | 'PARTIAL'
  | 'BETA'
  | 'PLANNED'
  | 'RESEARCH REQUIRED';

export type AppRoute =
  | '/'
  | '/generate/quick'
  | '/generate/scenarios'
  | '/build/scenario-builder'
  | '/observe/live-runs'
  | '/observe/telemetry'
  | '/observe/pipeline-health'
  | '/investigate/timeline'
  | '/investigate/incident'
  | '/investigate/security-intelligence'
  | '/catalog/provenance'
  | '/catalog/splunk-integrations'
  | '/system/connections';

export interface DomainDefinition {
  id: DomainId;
  label: string;
  shortLabel: string;
  maturity: ProductMaturity;
  description: string;
}

export interface NavigationItem {
  label: string;
  route: AppRoute;
  icon: string;
  advancedOnly?: boolean;
  availability?: ProductMaturity;
}

export interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

export const DOMAINS: DomainDefinition[] = [
  {
    id: 'netops',
    label: 'NetOps',
    shortLabel: 'NET',
    maturity: 'AVAILABLE',
    description: 'Network state, incidents, and native protocol telemetry',
  },
  {
    id: 'secops',
    label: 'SecOps',
    shortLabel: 'SEC',
    maturity: 'PARTIAL',
    description: 'Security scenarios and evidence where implemented',
  },
  {
    id: 'itops',
    label: 'ITOps',
    shortLabel: 'IT',
    maturity: 'PLANNED',
    description: 'Infrastructure and service behavior',
  },
  {
    id: 'observability',
    label: 'Observability',
    shortLabel: 'OBS',
    maturity: 'PARTIAL',
    description: 'Metrics, logs, traces, and cross-signal correlation',
  },
  {
    id: 'agentic-ai',
    label: 'Agentic AI',
    shortLabel: 'AI',
    maturity: 'BETA',
    description: 'Agent decisions, tools, policy, and downstream effects',
  },
  {
    id: 'supply-chain',
    label: 'Supply Chain',
    shortLabel: 'SCM',
    maturity: 'PLANNED',
    description: 'Software delivery lifecycle and artifact integrity',
  },
];

export const NAVIGATION: NavigationGroup[] = [
  {
    label: 'Home',
    items: [{ label: 'Overview', route: '/', icon: 'home' }],
  },
  {
    label: 'Generate',
    items: [
      { label: 'Quick Generate', route: '/generate/quick', icon: 'zap' },
      { label: 'Scenarios', route: '/generate/scenarios', icon: 'layers' },
    ],
  },
  {
    label: 'Build',
    items: [
      {
        label: 'Scenario Builder',
        route: '/build/scenario-builder',
        icon: 'workflow',
        advancedOnly: true,
      },
    ],
  },
  {
    label: 'Observe',
    items: [
      { label: 'Live Runs', route: '/observe/live-runs', icon: 'activity' },
      {
        label: 'Telemetry Explorer',
        route: '/observe/telemetry',
        icon: 'search',
        availability: 'PLANNED',
      },
      { label: 'Pipeline Health', route: '/observe/pipeline-health', icon: 'pulse' },
    ],
  },
  {
    label: 'Investigate',
    items: [
      {
        label: 'Incident Timeline',
        route: '/investigate/timeline',
        icon: 'clock',
        availability: 'PLANNED',
      },
      {
        label: 'Incident Investigation',
        route: '/investigate/incident',
        icon: 'inspect',
        availability: 'PLANNED',
      },
      {
        label: 'Security Intelligence',
        route: '/investigate/security-intelligence',
        icon: 'shield',
        availability: 'RESEARCH REQUIRED',
      },
    ],
  },
  {
    label: 'Catalog',
    items: [
      { label: 'Provenance', route: '/catalog/provenance', icon: 'badge' },
      {
        label: 'Splunk Integrations',
        route: '/catalog/splunk-integrations',
        icon: 'database',
      },
    ],
  },
  {
    label: 'System',
    items: [{ label: 'Connections', route: '/system/connections', icon: 'settings' }],
  },
];

export const ROUTE_TITLES = Object.fromEntries(
  NAVIGATION.flatMap((group) => group.items.map((item) => [item.route, item.label])),
) as Record<AppRoute, string>;

export function isAppRoute(value: string): value is AppRoute {
  return Object.prototype.hasOwnProperty.call(ROUTE_TITLES, value);
}
