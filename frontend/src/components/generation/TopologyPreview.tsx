import type { GenerationScenario } from '../../types/generation';

interface TopologyPreviewProps {
  scenario: GenerationScenario;
  activePhase?: string;
}

export function TopologyPreview({ scenario, activePhase }: TopologyPreviewProps) {
  if (scenario.nodes.length === 0 || scenario.zones.length === 0) {
    return (
      <div className="generation-empty" data-testid="topology-unavailable">
        Topology visualization not available for this scenario.
      </div>
    );
  }

  const width = 900;
  const height = 330;
  const zoneWidth = width / scenario.zones.length;
  const activeStep = scenario.timeline.find((step) => step.stage === activePhase);
  const positions = new Map<string, { x: number; y: number }>();

  scenario.zones.forEach((zone, zoneIndex) => {
    const nodes = scenario.nodes.filter((node) => node.zone_id === zone.zone_id);
    nodes.forEach((node, nodeIndex) => {
      positions.set(node.node_id, {
        x: zoneIndex * zoneWidth + zoneWidth / 2,
        y: 105 + nodeIndex * 115,
      });
    });
  });

  return (
    <div className="generation-topology" data-testid="scenario-topology">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${scenario.title} topology`}>
        {scenario.zones.map((zone, index) => (
          <g key={zone.zone_id}>
            <rect
              className="generation-topology__zone"
              x={index * zoneWidth + 10}
              y={20}
              width={zoneWidth - 20}
              height={height - 40}
              rx={8}
            />
            <text className="generation-topology__zone-label" x={index * zoneWidth + 24} y={45}>
              {zone.label}
            </text>
          </g>
        ))}

        {scenario.relationships.map((relationship) => {
          const source = positions.get(relationship.source_node_id);
          const target = positions.get(relationship.target_node_id);
          if (!source || !target) return null;
          return (
            <g key={relationship.relationship_id}>
              <line
                className="generation-topology__relationship"
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
              />
              <text
                className="generation-topology__edge-label"
                x={(source.x + target.x) / 2}
                y={(source.y + target.y) / 2 - 7}
              >
                {relationship.relationship_type}
              </text>
            </g>
          );
        })}

        {scenario.telemetry_paths.map((path) => {
          const source = positions.get(path.producer_node_id);
          const target = path.observer_node_id ? positions.get(path.observer_node_id) : null;
          if (!source || !target) return null;
          return (
            <line
              key={path.path_id}
              className="generation-topology__telemetry"
              x1={source.x}
              y1={source.y + 7}
              x2={target.x}
              y2={target.y + 7}
            />
          );
        })}

        {scenario.nodes.map((node) => {
          const position = positions.get(node.node_id);
          if (!position) return null;
          const runtimeState = activeStep?.state_changes[node.node_id] ?? 'normal';
          const incident = scenario.incident_path.includes(node.node_id);
          return (
            <g
              key={node.node_id}
              className={`generation-topology__node generation-topology__node--${runtimeState}`}
              transform={`translate(${position.x},${position.y})`}
              data-node-id={node.node_id}
            >
              <circle r={incident ? 31 : 27} />
              <text className="generation-topology__role" y={4}>{node.role.slice(0, 3).toUpperCase()}</text>
              <text className="generation-topology__node-label" y={48}>{node.node_id.replaceAll('-', ' ')}</text>
              <text className="generation-topology__state" y={64}>{runtimeState}</text>
            </g>
          );
        })}
      </svg>
      <div className="generation-topology__legend">
        <span><i className="legend-line legend-line--relationship" /> Relationship</span>
        <span><i className="legend-line legend-line--telemetry" /> Telemetry path</span>
        <span>Neutral NetSpout primitives · manifest-driven</span>
      </div>
    </div>
  );
}
