import { useMemo, useState } from 'react';
import type {
  GenerationRun,
  GenerationScenario,
  GenerationSource,
} from '../../types/generation';
import {
  buildScenarioVisualization,
  type VisualizationLens,
} from './scenarioVisualization';

interface TopologyPreviewProps {
  scenario: GenerationScenario;
  activePhase?: string;
  lens?: VisualizationLens;
  run?: GenerationRun | null;
  sources?: GenerationSource[];
  selectedNodeId?: string | null;
  selectedRelationshipId?: string | null;
  onSelectNode?: (nodeId: string | null) => void;
  onSelectRelationship?: (relationshipId: string | null) => void;
}

const stateStage = (run: GenerationRun | null | undefined, stage: string) =>
  run?.evidence.find((item) => item.stage === stage);

export function TopologyPreview({
  scenario,
  activePhase,
  lens = 'OVERVIEW',
  run,
  sources = [],
  selectedNodeId,
  selectedRelationshipId,
  onSelectNode,
  onSelectRelationship,
}: TopologyPreviewProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const model = useMemo(
    () => buildScenarioVisualization(scenario, activePhase, run),
    [scenario, activePhase, run],
  );
  if (scenario.nodes.length === 0 || scenario.zones.length === 0) {
    return (
      <div className="generation-empty" data-testid="topology-unavailable">
        Topology visualization not available for this scenario.
      </div>
    );
  }

  const selectedNode = model.nodes.find((item) => item.node.node_id === selectedNodeId);
  const selectedRelationship = model.relationships.find(
    (item) => item.relationship.relationship_id === selectedRelationshipId,
  );
  const fit = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div className="generation-topology" data-testid="scenario-topology">
      <div className="generation-topology__toolbar" aria-label="Topology view controls">
        <span>{scenario.visualization?.mode ?? 'AUTOMATIC'} LAYOUT</span>
        <button type="button" onClick={() => setZoom((value) => Math.min(1.8, value + 0.15))} aria-label="Zoom in">+</button>
        <button type="button" onClick={() => setZoom((value) => Math.max(0.65, value - 0.15))} aria-label="Zoom out">−</button>
        <button type="button" onClick={() => setPan((value) => ({ ...value, x: value.x - 45 }))} aria-label="Pan left">←</button>
        <button type="button" onClick={() => setPan((value) => ({ ...value, x: value.x + 45 }))} aria-label="Pan right">→</button>
        <button type="button" onClick={fit} aria-label="Fit topology to view">FIT</button>
      </div>
      <div className="generation-topology__viewport">
        <svg viewBox={`0 0 ${model.width} ${model.height}`} role="img" aria-label={`${scenario.title} topology, ${lens.toLowerCase()} lens`}>
          <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
            {scenario.zones.map((zone, index) => (
              <g key={zone.zone_id}>
                <rect
                  className="generation-topology__zone"
                  x={index * model.zoneWidth + 10}
                  y={20}
                  width={model.zoneWidth - 20}
                  height={model.height - 40}
                  rx={6}
                />
                <text className="generation-topology__zone-label" x={index * model.zoneWidth + 24} y={45}>
                  {zone.label}
                </text>
              </g>
            ))}

            {model.relationships.map(({ relationship, source, target, kind }, relationshipIndex) => {
              const isVertical = Math.abs(source.x - target.x) < 20;
              const labelOffset = ((relationshipIndex % 3) - 1) * 14;
              const dimmed = (lens === 'TELEMETRY' && kind !== 'TELEMETRY')
                || (lens === 'INCIDENT' && !scenario.incident_path.includes(source.node.node_id)
                  && !scenario.incident_path.includes(target.node.node_id));
              return (
                <g
                  key={relationship.relationship_id}
                  className={`generation-topology__edge generation-topology__edge--${kind.toLowerCase()} ${dimmed ? 'is-dimmed' : ''} ${selectedRelationshipId === relationship.relationship_id ? 'is-selected' : ''}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${source.node.label ?? source.node.node_id} ${relationship.relationship_type} ${target.node.label ?? target.node.node_id}`}
                  onClick={() => {
                    onSelectRelationship?.(relationship.relationship_id);
                    onSelectNode?.(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      onSelectRelationship?.(relationship.relationship_id);
                      onSelectNode?.(null);
                    }
                  }}
                >
                  <line className="generation-topology__edge-hitbox" x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
                  <line
                    className="generation-topology__relationship"
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                  />
                  <text
                    className="generation-topology__edge-label"
                    x={(source.x + target.x) / 2 + (isVertical ? 62 : 0)}
                    y={(source.y + target.y) / 2 + (isVertical ? 3 : -9 + labelOffset)}
                  >
                    {relationship.relationship_type}
                  </text>
                </g>
              );
            })}

            {scenario.telemetry_paths.map((path) => {
              const source = model.nodes.find((item) => item.node.node_id === path.producer_node_id);
              const target = path.observer_node_id
                ? model.nodes.find((item) => item.node.node_id === path.observer_node_id)
                : null;
              if (!source || !target) return null;
              const observed = stateStage(run, 'SPLUNK_OBSERVED')?.state === 'PROVEN';
              return (
                <g key={path.path_id} className={`generation-topology__telemetry-path ${lens === 'INCIDENT' ? 'is-dimmed' : ''} ${observed ? 'is-observed' : ''}`}>
                  <line
                    className="generation-topology__telemetry"
                    x1={source.x}
                    y1={source.y + 8}
                    x2={target.x}
                    y2={target.y + 8}
                  />
                  <text className="generation-topology__path-label" x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 + 22}>
                    {path.label ?? path.source_id} · {path.protocol ?? 'DECLARED'}
                  </text>
                </g>
              );
            })}

            {model.incidentEdges.map(({ source, target }) => (
              <line
                key={`${source.node.node_id}-${target.node.node_id}`}
                className={`generation-topology__incident ${lens === 'INCIDENT' ? 'is-emphasized' : ''}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
              />
            ))}

            {model.nodes.map(({ node, x, y, state, incident, generated }) => {
              const producesTelemetry = node.source_ids.length > 0;
              const isSplunk = node.role.toLowerCase() === 'splunk';
              const dimmed = (lens === 'TELEMETRY' && !producesTelemetry && !isSplunk)
                || (lens === 'INCIDENT' && !incident)
                || (lens === 'SPLUNK' && !producesTelemetry && !isSplunk);
              return (
                <g
                  key={node.node_id}
                  className={`generation-topology__node generation-topology__node--${state.toLowerCase()} ${incident ? 'is-incident' : ''} ${dimmed ? 'is-dimmed' : ''} ${selectedNodeId === node.node_id ? 'is-selected' : ''}`}
                  transform={`translate(${x},${y})`}
                  data-node-id={node.node_id}
                  data-layout={`${x.toFixed(2)}:${y.toFixed(2)}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${node.label ?? node.node_id}, ${node.role}, state ${state}`}
                  onClick={() => {
                    onSelectNode?.(node.node_id);
                    onSelectRelationship?.(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      onSelectNode?.(node.node_id);
                      onSelectRelationship?.(null);
                    }
                  }}
                >
                  <NodeShape role={node.role} incident={incident} />
                  <text className="generation-topology__role" y={4}>{node.role.slice(0, 3).toUpperCase()}</text>
                  <text className="generation-topology__node-label" y={50}>{node.label ?? node.node_id.replaceAll('-', ' ')}</text>
                  <text className="generation-topology__state" y={66}>{state} {generated > 0 ? `· ${generated} EVENTS` : ''}</text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {(selectedNode || selectedRelationship) && (
        <aside className="generation-topology__inspector" aria-label="Topology technical inspector">
          {selectedNode && (
            <>
              <div><span>Selected entity</span><strong>{selectedNode.node.label ?? selectedNode.node.node_id}</strong></div>
              <dl>
                <div><dt>Role</dt><dd>{selectedNode.node.role}</dd></div>
                <div><dt>Technology</dt><dd>{selectedNode.node.technology_id}</dd></div>
                <div><dt>State</dt><dd>{selectedNode.state}</dd></div>
                <div><dt>Generated</dt><dd>{selectedNode.generated}</dd></div>
                <div><dt>Splunk observed</dt><dd>{stateStage(run, 'SPLUNK_OBSERVED')?.count ?? 0}</dd></div>
              </dl>
              {selectedNode.node.description && <p>{selectedNode.node.description}</p>}
              {selectedNode.node.source_ids.map((sourceId) => {
                const source = sources.find((item) => item.source_id === sourceId);
                return (
                  <div className="generation-topology__source" key={sourceId}>
                    <code>{sourceId}</code>
                    <span>{source?.native_contract.contract_id ?? 'Contract not loaded'}</span>
                    <span>{source?.provenance.join(' · ') ?? 'Provenance unavailable'}</span>
                  </div>
                );
              })}
            </>
          )}
          {selectedRelationship && (
            <>
              <div><span>Selected connection</span><strong>{selectedRelationship.relationship.relationship_type}</strong></div>
              <dl>
                <div><dt>Source</dt><dd>{selectedRelationship.source.node.label ?? selectedRelationship.source.node.node_id}</dd></div>
                <div><dt>Destination</dt><dd>{selectedRelationship.target.node.label ?? selectedRelationship.target.node.node_id}</dd></div>
                <div><dt>Protocol</dt><dd>{selectedRelationship.relationship.protocol ?? 'NOT DECLARED'}</dd></div>
                <div><dt>State</dt><dd>{model.activeStep?.stage ?? 'NOT RUN'}</dd></div>
              </dl>
              <p>{selectedRelationship.relationship.purpose ?? 'No operational purpose is declared.'}</p>
              {selectedRelationship.relationship.incident_relevance && (
                <p><strong>Incident relevance:</strong> {selectedRelationship.relationship.incident_relevance}</p>
              )}
            </>
          )}
        </aside>
      )}

      <div className="generation-topology__legend">
        <span><i className="legend-line legend-line--relationship" /> Operational path</span>
        <span><i className="legend-line legend-line--telemetry" /> Telemetry path</span>
        <span><i className="legend-line legend-line--incident" /> Incident path</span>
        <span>State is expressed by label, shape and restrained color</span>
      </div>
    </div>
  );
}

function NodeShape({ role, incident }: { role: string; incident: boolean }) {
  const normalized = role.toLowerCase();
  if (normalized === 'user' || normalized === 'endpoint') {
    return <circle r={incident ? 32 : 29} />;
  }
  if (['router', 'switch', 'firewall', 'wireless'].includes(normalized)) {
    return <polygon points="-32,0 -16,-27 16,-27 32,0 16,27 -16,27" />;
  }
  if (normalized === 'cloud') {
    return <ellipse rx={36} ry={25} />;
  }
  return (
    <rect
      x={incident ? -36 : -33}
      y={incident ? -29 : -26}
      width={incident ? 72 : 66}
      height={incident ? 58 : 52}
      rx={7}
    />
  );
}
