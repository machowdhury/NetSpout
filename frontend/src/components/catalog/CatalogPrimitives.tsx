import { ExternalLink } from 'lucide-react';
import type {
  CatalogEvidence,
  CimMapping,
  SourcetypeClaim,
  VerificationState,
} from '../../types/catalog';
import { ProvenanceBadge, StatusBadge } from '../ui/SystemPrimitives';
import { missingLabel, sourcetypeAuthorityLabels } from './catalogDisplay';

export function ValueList({
  values,
  empty,
  code = false,
}: {
  values: string[];
  empty: string;
  code?: boolean;
}) {
  if (values.length === 0) return <span className="catalog-empty">{empty}</span>;
  return (
    <div className="catalog-chip-list">
      {values.map((value) =>
        code ? <code key={value}>{value}</code> : <span key={value}>{value}</span>,
      )}
    </div>
  );
}

export function SourcetypeList({
  claims,
  empty,
}: {
  claims: SourcetypeClaim[];
  empty: string;
}) {
  if (claims.length === 0) return <span className="catalog-empty">{empty}</span>;
  return (
    <div className="sourcetype-list">
      {claims.map((claim) => (
        <div key={`${claim.name}-${claim.authority}`}>
          <code>{claim.name}</code>
          <span data-authority={claim.authority}>{sourcetypeAuthorityLabels[claim.authority]}</span>
        </div>
      ))}
    </div>
  );
}

export function CimMappingList({
  mappings,
  empty,
}: {
  mappings: CimMapping[];
  empty: string;
}) {
  if (mappings.length === 0) return <span className="catalog-empty">{empty}</span>;
  return (
    <div className="catalog-chip-list">
      {mappings.map((mapping) => (
        <span key={mapping.name}>
          {mapping.name}
          <StatusBadge status={mapping.verification_state.replaceAll('_', ' ')} />
        </span>
      ))}
    </div>
  );
}

export function EvidenceList({
  evidenceIds,
  evidenceById,
  state,
}: {
  evidenceIds: string[];
  evidenceById: Map<string, CatalogEvidence>;
  state: VerificationState;
}) {
  const records = evidenceIds.flatMap((id) => {
    const record = evidenceById.get(id);
    return record ? [record] : [];
  });

  if (records.length === 0) {
    return <span className="catalog-empty">{missingLabel(state, true)}</span>;
  }

  return (
    <div className="evidence-list">
      {records.map((record) => {
        const external = /^https?:\/\//.test(record.reference);
        return (
          <article key={record.evidence_id}>
            <div className="evidence-list__title">
              <strong>{record.title}</strong>
              <StatusBadge status={record.verification_state.replaceAll('_', ' ')} />
            </div>
            <span>{record.publisher}</span>
            <p>{record.notes}</p>
            {external ? (
              <a href={record.reference} target="_blank" rel="noopener noreferrer">
                View evidence <ExternalLink />
              </a>
            ) : (
              <code>{record.reference}</code>
            )}
            <ProvenanceBadge state={record.provenance} />
          </article>
        );
      })}
    </div>
  );
}
