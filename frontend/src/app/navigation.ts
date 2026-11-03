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
  | '/explore'
  | '/generate/quick'
  | '/generate/scenarios'
  | '/generate/unified'
  | '/build/studio'
  | '/build/industry-studio'
  | '/build/scenario-builder'
  | '/observe/live-runs'
  | '/investigate'
  | '/observe/dashboards'
  | '/observe/pipeline-health'
  | '/security-content'
  | '/catalog/provenance'
  | '/catalog/security-sources'
  | '/catalog/cisco-100'
  | '/catalog/cisco-coverage'
  | '/catalog/splunk-integrations'
  | '/system/connections'
  | '/destinations'
  | '/guided-workflow';

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

// Five primary destinations (Overview, Scenarios, Live Runs, Investigate, Dashboards) plus Reference. Every previous page is still
// reachable; routes that were placeholders without a runtime path are no longer offered and redirect to the page that now does the job.
export const NAVIGATION: NavigationGroup[] = [
  {
    label: 'Overview',
    items: [{ label: 'Overview', route: '/', icon: 'home' }],
  },
  {
    label: 'Scenarios',
    items: [
      { label: 'Use Case Explorer', route: '/explore', icon: 'search', availability: 'BETA' },
      { label: 'Quick Generate', route: '/generate/quick', icon: 'zap' },
      { label: 'Guided Scenarios', route: '/generate/scenarios', icon: 'layers' },
      { label: 'Run in 6 Steps', route: '/generate/unified', icon: 'workflow' },
      { label: 'Scenario Studio', route: '/build/studio', icon: 'studio' },
      { label: 'Industry Studio', route: '/build/industry-studio', icon: 'industry' },
      { label: 'Scenario Builder', route: '/build/scenario-builder', icon: 'workflow', advancedOnly: true },
    ],
  },
  {
    label: 'Live Runs',
    items: [
      { label: 'Live Runs', route: '/observe/live-runs', icon: 'activity' },
      { label: 'Pipeline Health', route: '/observe/pipeline-health', icon: 'pulse' },
    ],
  },
  {
    label: 'Investigate',
    items: [
      { label: 'Investigate a Run', route: '/investigate', icon: 'inspect' },
      { label: 'Detection Explorer', route: '/security-content', icon: 'shield', availability: 'BETA' },
    ],
  },
  {
    label: 'Dashboards',
    items: [{ label: 'Dashboard Studio', route: '/observe/dashboards', icon: 'dashboard' }],
  },
  {
    label: 'Reference',
    items: [
      { label: 'Cisco 100', route: '/catalog/cisco-100', icon: 'catalog' },
      { label: 'Cisco Coverage', route: '/catalog/cisco-coverage', icon: 'network' },
      { label: 'Security Sources', route: '/catalog/security-sources', icon: 'shield' },
      { label: 'Provenance', route: '/catalog/provenance', icon: 'badge' },
      { label: 'Splunk Integrations', route: '/catalog/splunk-integrations', icon: 'database' },
      { label: 'Connections', route: '/system/connections', icon: 'settings' },
      { label: 'Destination Manager', route: '/destinations', icon: 'server' },
      { label: 'Guided Workflow', route: '/guided-workflow', icon: 'workflow' },
    ],
  },
];

// Bookmarked hashes of the retired placeholder pages land on the page that replaced them.
export const LEGACY_REDIRECTS: Record<string, AppRoute> = {
  '/observe/telemetry': '/observe/live-runs',
  '/investigate/timeline': '/investigate',
  '/investigate/incident': '/investigate',
  '/investigate/security-intelligence': '/investigate',
};

export const ROUTE_TITLES = Object.fromEntries(
  NAVIGATION.flatMap((group) => group.items.map((item) => [item.route, item.label])),
) as Record<AppRoute, string>;

export function isAppRoute(value: string): value is AppRoute {
  return Object.prototype.hasOwnProperty.call(ROUTE_TITLES, value);
}
