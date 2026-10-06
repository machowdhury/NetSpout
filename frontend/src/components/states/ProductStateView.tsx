import { ArrowLeft, Construction, FileSearch, ShieldAlert } from 'lucide-react';
import type { AppRoute, ProductMaturity } from '../../app/navigation';
import { Panel, StatePanel, StatusBadge } from '../ui/SystemPrimitives';

const copy: Record<
  ProductMaturity,
  { kind: 'empty' | 'unavailable' | 'degraded'; message: string }
> = {
  AVAILABLE: {
    kind: 'empty',
    message: 'No runtime evidence is available for this view yet.',
  },
  PARTIAL: {
    kind: 'degraded',
    message: 'Some supporting capabilities exist, but this unified view is not complete.',
  },
  BETA: {
    kind: 'degraded',
    message: 'This capability is in beta and must not be treated as production evidence.',
  },
  PLANNED: {
    kind: 'unavailable',
    message: 'This experience is planned and has no supported runtime path.',
  },
  'RESEARCH REQUIRED': {
    kind: 'unavailable',
    message: 'Authoritative source research is required before this capability can be enabled.',
  },
};

export function ProductStateView({
  title,
  maturity,
  description,
  nextPhase,
  onNavigate,
}: {
  title: string;
  maturity: ProductMaturity;
  description: string;
  nextPhase?: string;
  onNavigate: (route: AppRoute) => void;
}) {
  const state = copy[maturity];
  const Icon =
    maturity === 'RESEARCH REQUIRED'
      ? FileSearch
      : maturity === 'PARTIAL' || maturity === 'BETA'
        ? ShieldAlert
        : Construction;

  return (
    <div className="workspace-stack workspace-stack--narrow">
      <Panel>
        <div className="product-state-header">
          <div className="product-state-header__icon">
            <Icon />
          </div>
          <div>
            <div className="product-state-header__status">
              <StatusBadge status={maturity} />
              {nextPhase && <span>{nextPhase}</span>}
            </div>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
        </div>
      </Panel>
      <StatePanel kind={state.kind} title={maturity} message={state.message} />
      <button type="button" className="button button--secondary button--self" onClick={() => onNavigate('/')}>
        <ArrowLeft /> Return to overview
      </button>
    </div>
  );
}
