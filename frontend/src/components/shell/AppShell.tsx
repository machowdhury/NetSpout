import { useMemo, useState } from 'react';
import type { ComponentType, ReactNode } from 'react';
import {
  Activity,
  BadgeCheck,
  BookOpen,
  Clock3,
  Database,
  Gauge,
  Home,
  Layers3,
  Menu,
  Network,
  Search,
  Settings2,
  Shield,
  Sparkles,
  Workflow,
  X,
  Zap,
} from 'lucide-react';
import {
  DOMAINS,
  NAVIGATION,
  ROUTE_TITLES,
  type AppRoute,
  type DomainId,
  type ExperienceMode,
} from '../../app/navigation';
import { StatusBadge } from '../ui/SystemPrimitives';

const iconMap: Record<string, ComponentType<{ className?: string }>> = {
  activity: Activity,
  badge: BadgeCheck,
  catalog: BookOpen,
  clock: Clock3,
  database: Database,
  home: Home,
  inspect: Search,
  layers: Layers3,
  network: Network,
  pulse: Gauge,
  search: Search,
  settings: Settings2,
  shield: Shield,
  studio: Sparkles,
  workflow: Workflow,
  zap: Zap,
};

interface AppShellProps {
  route: AppRoute;
  domain: DomainId;
  mode: ExperienceMode;
  liveFeedConnected: boolean;
  onNavigate: (route: AppRoute) => void;
  onDomainChange: (domain: DomainId) => void;
  onModeChange: (mode: ExperienceMode) => void;
  children: ReactNode;
}

export function AppShell({
  route,
  domain,
  mode,
  liveFeedConnected,
  onNavigate,
  onDomainChange,
  onModeChange,
  children,
}: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const activeDomain = useMemo(
    () => DOMAINS.find((item) => item.id === domain) ?? DOMAINS[0],
    [domain],
  );

  const navigate = (nextRoute: AppRoute) => {
    onNavigate(nextRoute);
    setMobileNavOpen(false);
  };

  const navigation = (
    <nav className="app-nav" aria-label="Primary navigation">
      {NAVIGATION.map((group) => {
        const items = group.items.filter((item) => mode === 'advanced' || !item.advancedOnly);
        if (items.length === 0) return null;

        return (
          <div className="app-nav__group" key={group.label}>
            <div className="app-nav__group-label">{group.label}</div>
            {items.map((item) => {
              const Icon = iconMap[item.icon] ?? Activity;
              const selected = item.route === route;
              return (
                <button
                  type="button"
                  key={item.route}
                  className={`app-nav__item ${selected ? 'app-nav__item--active' : ''}`}
                  aria-current={selected ? 'page' : undefined}
                  onClick={() => navigate(item.route)}
                >
                  <Icon className="app-nav__icon" />
                  <span>{item.label}</span>
                  {item.availability && (
                    <span className="app-nav__availability">{item.availability}</span>
                  )}
                </button>
              );
            })}
          </div>
        );
      })}
    </nav>
  );

  return (
    <div className={`product-shell product-shell--${mode}`}>
      <aside className="product-sidebar">
        <div className="product-brand">
          <div className="product-brand__mark" aria-hidden="true">
            <Network />
          </div>
          <div>
            <div className="product-brand__name">NetSpout</div>
            <div className="product-brand__subtitle">Unified Enterprise Telemetry Lab</div>
          </div>
        </div>
        {navigation}
        <div className="product-sidebar__footer">
          <span className={`runtime-dot ${liveFeedConnected ? 'runtime-dot--active' : ''}`} />
          <div>
            <strong>{liveFeedConnected ? 'Live feed connected' : 'Live feed unavailable'}</strong>
            <span>Runtime evidence only</span>
          </div>
        </div>
      </aside>

      {mobileNavOpen && (
        <div className="mobile-nav-backdrop" role="presentation" onClick={() => setMobileNavOpen(false)}>
          <aside
            className="mobile-nav"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mobile-nav__header">
              <div className="product-brand product-brand--mobile">
                <div className="product-brand__mark">
                  <Network />
                </div>
                <div>
                  <div className="product-brand__name">NetSpout</div>
                  <div className="product-brand__subtitle">Telemetry Lab</div>
                </div>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="Close navigation"
                onClick={() => setMobileNavOpen(false)}
              >
                <X />
              </button>
            </div>
            {navigation}
          </aside>
        </div>
      )}

      <div className="product-main">
        <header className="product-header">
          <div className="product-header__title-group">
            <button
              type="button"
              className="icon-button product-header__menu"
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu />
            </button>
            <div>
              <div className="product-header__eyebrow">{activeDomain.label}</div>
              <h1>{ROUTE_TITLES[route]}</h1>
            </div>
          </div>

          <div className="product-header__controls">
            <div className="mode-switch" aria-label="Experience mode">
              <button
                type="button"
                className={mode === 'simple' ? 'mode-switch__active' : ''}
                aria-pressed={mode === 'simple'}
                onClick={() => onModeChange('simple')}
              >
                Simple
              </button>
              <button
                type="button"
                className={mode === 'advanced' ? 'mode-switch__active' : ''}
                aria-pressed={mode === 'advanced'}
                onClick={() => onModeChange('advanced')}
              >
                Advanced
              </button>
            </div>
            <div className="product-header__runtime">
              <StatusBadge status={liveFeedConnected ? 'STREAMING' : 'NOT AVAILABLE'} />
            </div>
          </div>
        </header>

        <section className="domain-selector" aria-label="Operational domain">
          <div className="domain-selector__scroll">
            {DOMAINS.map((item) => (
              <button
                type="button"
                key={item.id}
                className={`domain-button ${item.id === domain ? 'domain-button--active' : ''}`}
                aria-pressed={item.id === domain}
                title={item.description}
                onClick={() => onDomainChange(item.id)}
              >
                <span className="domain-button__code">{item.shortLabel}</span>
                <span className="domain-button__label">{item.label}</span>
                <StatusBadge status={item.maturity} />
              </button>
            ))}
          </div>
        </section>

        <main className="product-workspace" id="main-content">
          {children}
        </main>

        <footer className="product-footer">
          <span>Simulate enterprise incidents. Generate authentic telemetry.</span>
          <span className="product-footer__flow">
            Choose <b>→</b> Run <b>→</b> Observe <b>→</b> Correlate <b>→</b> Investigate
          </span>
        </footer>
      </div>
    </div>
  );
}
