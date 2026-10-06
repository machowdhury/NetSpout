import type {
  GenerationRun,
  GenerationScenario,
  TimelineStep,
  TopologyNode,
  TopologyRelationship,
} from '../../types/generation';

export type VisualizationLens = 'OVERVIEW' | 'TELEMETRY' | 'INCIDENT' | 'SPLUNK';

export interface PositionedNode {
  node: TopologyNode;
  x: number;
  y: number;
  state: string;
  incident: boolean;
  generated: number;
}

export interface PositionedRelationship {
  relationship: TopologyRelationship;
  source: PositionedNode;
  target: PositionedNode;
  kind: 'OPERATIONAL' | 'TELEMETRY';
}

export interface ScenarioVisualizationModel {
  width: number;
  height: number;
  zoneWidth: number;
  nodes: PositionedNode[];
  relationships: PositionedRelationship[];
  incidentEdges: Array<{ source: PositionedNode; target: PositionedNode }>;
  activeStep: TimelineStep | null;
}

const normalizedState = (value: string | undefined) => (value ?? 'UNKNOWN').toUpperCase();

function accumulatedStates(scenario: GenerationScenario, activePhase?: string): Map<string, string> {
  const states = new Map<string, string>();
  const activeIndex = activePhase
    ? scenario.timeline.findIndex((item) => item.stage === activePhase)
    : -1;
  const through = activeIndex >= 0 ? activeIndex : -1;
  if (through < 0) return states;
  scenario.timeline.slice(0, through + 1).forEach((step) => {
    const changes = {
      ...step.state_changes,
      ...(step.entity_state_changes ?? {}),
    };
    Object.entries(changes).forEach(([nodeId, state]) => {
      if (scenario.nodes.some((node) => node.node_id === nodeId)) {
        states.set(nodeId, normalizedState(state));
      }
    });
  });
  return states;
}

export function buildScenarioVisualization(
  scenario: GenerationScenario,
  activePhase?: string,
  run?: GenerationRun | null,
): ScenarioVisualizationModel {
  const width = Math.max(960, scenario.zones.length * 360);
  const zoneWidth = width / Math.max(scenario.zones.length, 1);
  const maxNodes = Math.max(
    1,
    ...scenario.zones.map(
      (zone) => scenario.nodes.filter((node) => node.zone_id === zone.zone_id).length,
    ),
  );
  const height = Math.max(380, maxNodes * 128 + 120);
  const states = accumulatedStates(scenario, activePhase);
  const positions = new Map<string, PositionedNode>();

  scenario.zones.forEach((zone, zoneIndex) => {
    const nodes = scenario.nodes.filter((node) => node.zone_id === zone.zone_id);
    nodes.forEach((node, nodeIndex) => {
      const horizontal = scenario.visualization?.direction !== 'TOP_TO_BOTTOM';
      const x = horizontal
        ? zoneIndex * zoneWidth + zoneWidth / 2
        : 150 + nodeIndex * 220;
      const y = horizontal
        ? 110 + nodeIndex * 128
        : zoneIndex * (height / scenario.zones.length) + height / scenario.zones.length / 2;
      positions.set(node.node_id, {
        node,
        x,
        y,
        state: states.get(node.node_id) ?? (run ? 'NORMAL' : 'UNKNOWN'),
        incident: scenario.incident_path.includes(node.node_id),
        generated: run?.channel_results?.length
          ? run.channel_results
            .filter((channel) => node.source_ids.includes(channel.source_id))
            .reduce((total, channel) => total + (channel.evidence.find((item) => item.stage === 'GENERATED')?.count ?? 0), 0)
          : run?.events.filter((event) => node.source_ids.includes(event.source_id)).length ?? 0,
      });
    });
  });

  const nodes = scenario.nodes
    .map((node) => positions.get(node.node_id))
    .filter((node): node is PositionedNode => Boolean(node));
  const relationships = scenario.relationships
    .map((relationship) => {
      const source = positions.get(relationship.source_node_id);
      const target = positions.get(relationship.target_node_id);
      if (!source || !target) return null;
      const kind = relationship.telemetry_source_ids?.length
        || relationship.relationship_type.toLowerCase().includes('telemetry')
        ? 'TELEMETRY'
        : 'OPERATIONAL';
      return { relationship, source, target, kind } as PositionedRelationship;
    })
    .filter((relationship): relationship is PositionedRelationship => Boolean(relationship));

  const incidentEdges = scenario.incident_path.slice(0, -1).flatMap((nodeId, index) => {
    const source = positions.get(nodeId);
    const target = positions.get(scenario.incident_path[index + 1]);
    return source && target ? [{ source, target }] : [];
  });

  return {
    width,
    height,
    zoneWidth,
    nodes,
    relationships,
    incidentEdges,
    activeStep: scenario.timeline.find((step) => step.stage === activePhase) ?? null,
  };
}

export function deterministicLayoutSignature(scenario: GenerationScenario): string {
  const model = buildScenarioVisualization(scenario);
  return model.nodes
    .map(({ node, x, y }) => `${node.node_id}:${x.toFixed(2)}:${y.toFixed(2)}`)
    .join('|');
}
