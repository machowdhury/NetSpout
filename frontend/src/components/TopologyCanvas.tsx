import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Router as RouterIcon,
  Network,
  GitFork,
  Box,
  Server,
  Database,
  Globe,
  Radio,
  Cloud,
  Cpu,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Sliders
} from 'lucide-react';
import type { Node, Edge, NodeType, TopologyState } from '../types/topology';
import { PALETTE_ITEMS } from './NodePalette';

interface TopologyCanvasProps {
  topology: TopologyState;
  onUpdateTopology: (topology: TopologyState) => void;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  selectedEdgeId: string | null;
  onSelectEdge: (edgeId: string | null) => void;
  isRunning: boolean;
  showZones?: boolean;
  onInspectNode?: (node: Node) => void;
}

interface DragState {
  isDragging: boolean;
  nodeId: string | null;
  startX: number;
  startY: number;
  initialNodeX: number;
  initialNodeY: number;
}

interface WireDraft {
  sourceNodeId: string;
  sourceAnchor: 'top' | 'right' | 'bottom' | 'left';
  currentX: number;
  currentY: number;
}

export const TopologyCanvas: React.FC<TopologyCanvasProps> = ({
  topology,
  onUpdateTopology,
  selectedNodeId,
  onSelectNode,
  selectedEdgeId,
  onSelectEdge,
  isRunning,
  showZones = true,
  onInspectNode
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    nodeId: null,
    startX: 0,
    startY: 0,
    initialNodeX: 0,
    initialNodeY: 0
  });

  const [wireDraft, setWireDraft] = useState<WireDraft | null>(null);

  // Helper to get Anchor Coordinates for a node
  const getAnchorCoords = useCallback((node: Node, anchor: 'top' | 'right' | 'bottom' | 'left') => {
    const width = 160;
    const height = 70;
    switch (anchor) {
      case 'top':
        return { x: node.x + width / 2, y: node.y };
      case 'right':
        return { x: node.x + width, y: node.y + height / 2 };
      case 'bottom':
        return { x: node.x + width / 2, y: node.y + height };
      case 'left':
        return { x: node.x, y: node.y + height / 2 };
    }
  }, []);

  // Keyboard Delete Handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodeId) {
          const nextNodes = topology.nodes.filter((n) => n.id !== selectedNodeId);
          const nextEdges = topology.edges.filter(
            (edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId
          );
          onUpdateTopology({ nodes: nextNodes, edges: nextEdges });
          onSelectNode(null);
        } else if (selectedEdgeId) {
          const nextEdges = topology.edges.filter((e) => e.id !== selectedEdgeId);
          onUpdateTopology({ ...topology, edges: nextEdges });
          onSelectEdge(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, selectedEdgeId, topology, onUpdateTopology, onSelectNode, onSelectEdge]);

  // Drop item from palette onto canvas
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('application/node-type') as NodeType;
    const customVendor = e.dataTransfer.getData('application/node-vendor');
    const customSourcetype = e.dataTransfer.getData('application/node-sourcetype');
    const customName = e.dataTransfer.getData('application/node-name');
    if (!type || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - pan.x) / zoom;
    const mouseY = (e.clientY - rect.top - pan.y) / zoom;

    const paletteDef = PALETTE_ITEMS.find((p) => p.type === type);
    const id = `node-${type}-${Date.now().toString().slice(-4)}`;
    const newNode: Node = {
      id,
      name: customName || `${paletteDef?.name || type} ${topology.nodes.length + 1}`,
      type,
      x: Math.max(20, mouseX - 80),
      y: Math.max(20, mouseY - 35),
      ip_address: paletteDef?.defaultIp || '10.0.1.1',
      status: 'active',
      vendor: customVendor || paletteDef?.defaultVendor || 'generic',
      sourcetype: customSourcetype || paletteDef?.defaultSourcetype
    };

    onUpdateTopology({
      ...topology,
      nodes: [...topology.nodes, newNode]
    });
    onSelectNode(id);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  // Node Dragging on Canvas
  const handleNodeMouseDown = (e: React.MouseEvent, node: Node) => {
    e.stopPropagation();
    onSelectNode(node.id);
    onSelectEdge(null);
    setDragState({
      isDragging: true,
      nodeId: node.id,
      startX: e.clientX,
      startY: e.clientY,
      initialNodeX: node.x,
      initialNodeY: node.y
    });
  };

  // Wire Anchor Connection Initiator
  const handleAnchorMouseDown = (
    e: React.MouseEvent,
    node: Node,
    anchor: 'top' | 'right' | 'bottom' | 'left'
  ) => {
    e.stopPropagation();
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setWireDraft({
      sourceNodeId: node.id,
      sourceAnchor: anchor,
      currentX: (e.clientX - rect.left - pan.x) / zoom,
      currentY: (e.clientY - rect.top - pan.y) / zoom
    });
  };

  // Canvas Mouse Move
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const currentCanvasX = (e.clientX - rect.left - pan.x) / zoom;
    const currentCanvasY = (e.clientY - rect.top - pan.y) / zoom;

    if (dragState.isDragging && dragState.nodeId) {
      const deltaX = (e.clientX - dragState.startX) / zoom;
      const deltaY = (e.clientY - dragState.startY) / zoom;
      const nextNodes = topology.nodes.map((n) => {
        if (n.id === dragState.nodeId) {
          return {
            ...n,
            x: Math.max(10, Math.round(dragState.initialNodeX + deltaX)),
            y: Math.max(10, Math.round(dragState.initialNodeY + deltaY))
          };
        }
        return n;
      });
      onUpdateTopology({ ...topology, nodes: nextNodes });
    } else if (wireDraft) {
      setWireDraft((prev) => (prev ? { ...prev, currentX: currentCanvasX, currentY: currentCanvasY } : null));
    } else if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    }
  };

  // Mouse Up
  const handleMouseUp = (e: React.MouseEvent) => {
    if (dragState.isDragging) {
      setDragState({ isDragging: false, nodeId: null, startX: 0, startY: 0, initialNodeX: 0, initialNodeY: 0 });
    }

    if (wireDraft) {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const dropX = (e.clientX - rect.left - pan.x) / zoom;
        const dropY = (e.clientY - rect.top - pan.y) / zoom;

        const targetNode = topology.nodes.find(
          (n) =>
            n.id !== wireDraft.sourceNodeId &&
            dropX >= n.x &&
            dropX <= n.x + 160 &&
            dropY >= n.y &&
            dropY <= n.y + 70
        );

        if (targetNode) {
          const edgeId = `edge-${wireDraft.sourceNodeId}-${targetNode.id}-${Date.now().toString().slice(-4)}`;
          const exists = topology.edges.some(
            (ed) =>
              (ed.source === wireDraft.sourceNodeId && ed.target === targetNode.id) ||
              (ed.source === targetNode.id && ed.target === wireDraft.sourceNodeId)
          );

          if (!exists) {
            const newEdge: Edge = {
              id: edgeId,
              source: wireDraft.sourceNodeId,
              target: targetNode.id,
              source_port: wireDraft.sourceAnchor,
              target_port: 'left',
              status: 'up'
            };
            onUpdateTopology({
              ...topology,
              edges: [...topology.edges, newEdge]
            });
          }
        }
      }
      setWireDraft(null);
    }

    if (isPanning) {
      setIsPanning(false);
    }
  };

  // Canvas Pan (Drag canvas background)
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.target === containerRef.current || (e.target as HTMLElement).tagName === 'svg') {
      onSelectNode(null);
      onSelectEdge(null);
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const getNodeIcon = (type: NodeType) => {
    switch (type) {
      case 'client_external':
        return Globe;
      case 'firewall':
      case 'vpn_gateway':
        return ShieldAlert;
      case 'load_balancer':
        return GitFork;
      case 'router':
        return RouterIcon;
      case 'switch':
        return Network;
      case 'web_server':
        return Server;
      case 'database':
      case 'storage_san':
      case 'storage_nas':
        return Database;
      case 'subnet':
        return Box;
      case 'wireless_ap':
      case 'wlc_controller':
        return Radio;
      case 'sase_proxy':
      case 'cloud_transit':
        return Cloud;
      case 'optical_core':
      case 'iot_sensor':
        return Cpu;
      default:
        return Server;
    }
  };

  return (
    <div
      ref={containerRef}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onMouseDown={handleCanvasMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      className="flex-1 h-full relative overflow-hidden bg-[#0B0F19] select-none cursor-crosshair"
      style={{
        backgroundImage: `radial-gradient(#1E293B 1.25px, transparent 1.25px)`,
        backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
        backgroundPosition: `${pan.x}px ${pan.y}px`
      }}
    >
      {/* Zoom / Canvas Controls Float */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1 backdrop-blur shadow-lg">
        <button
          onClick={() => setZoom((z) => Math.min(2.0, z + 0.1))}
          className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}
          className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
          title="Reset View"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        <span className="text-[11px] font-mono text-slate-500 px-2">
          {Math.round(zoom * 100)}%
        </span>
      </div>

      {/* Top HUD Banner with Canvas Info & Status */}
      <div className="absolute top-4 left-44 right-4 z-10 flex items-center justify-between bg-slate-900/90 border border-slate-800 rounded-lg px-4 py-2 backdrop-blur shadow-lg">
        <div className="flex items-center gap-3">
          <span className="flex h-2.5 w-2.5 relative">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isRunning ? 'bg-emerald-400 opacity-75' : 'bg-amber-400 opacity-75'}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isRunning ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
          </span>
          <div>
            <b className="text-xs font-mono text-slate-200">
              NetSpout Visual NOC Studio — {isRunning ? 'Live Telemetry Active' : 'Simulation Paused'}
            </b>
            <p className="text-[10px] text-slate-400 font-mono m-0">
              Model-Driven Telemetry streaming directly into Splunk HEC. Click nodes to inspect, drag anchors to wire links.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono bg-cyan-950/80 border border-cyan-700/60 text-cyan-300 px-2.5 py-1 rounded">
            {topology.nodes.length} Active Nodes | {topology.edges.length} Links
          </span>
        </div>
      </div>

      {/* SVG Canvas for Wires and Dynamic Links */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0'
        }}
      >
        {/* Security Zones Layer (Rendered below wires and nodes) */}
        {showZones && topology.zones && topology.zones.map((zone) => {
          const zoneColor = zone.color || '#3b82f6';
          return (
            <g key={zone.id} className="pointer-events-none select-none">
              <rect
                x={zone.x}
                y={zone.y}
                width={zone.width}
                height={zone.height}
                rx={14}
                ry={14}
                fill={zoneColor}
                fillOpacity={zone.opacity || 0.12}
                stroke={zoneColor}
                strokeWidth="1.5"
                strokeDasharray="6,4"
              />
              <rect
                x={zone.x + 12}
                y={zone.y - 12}
                width={Math.max(140, zone.name.length * 7.5 + 40)}
                height={22}
                rx={6}
                fill="#090d16"
                stroke={zoneColor}
                strokeWidth="1"
              />
              <circle cx={zone.x + 22} cy={zone.y - 1} r="3.5" fill={zoneColor} />
              <text
                x={zone.x + 32}
                y={zone.y + 2.5}
                fill={zoneColor}
                fontSize="10"
                fontWeight="bold"
                fontFamily="monospace"
                letterSpacing="0.05em"
              >
                {zone.name.toUpperCase()}
              </text>
            </g>
          );
        })}

        {/* Existing Topology Edges */}
        {topology.edges.map((edge) => {
          const sourceNode = topology.nodes.find((n) => n.id === edge.source);
          const targetNode = topology.nodes.find((n) => n.id === edge.target);
          if (!sourceNode || !targetNode) return null;

          const sX = sourceNode.x + 160;
          const sY = sourceNode.y + 35;
          const tX = targetNode.x;
          const tY = targetNode.y + 35;

          const isSelected = selectedEdgeId === edge.id;
          const isBreached =
            edge.status === 'breached' ||
            sourceNode.status === 'breached' ||
            targetNode.status === 'breached';

          const dx = Math.abs(tX - sX) * 0.5;
          const pathData = `M ${sX} ${sY} C ${sX + dx} ${sY}, ${tX - dx} ${tY}, ${tX} ${tY}`;

          return (
            <g key={edge.id} className="pointer-events-auto cursor-pointer" onClick={() => onSelectEdge(edge.id)}>
              <path d={pathData} fill="none" stroke="transparent" strokeWidth="16" />
              <path
                d={pathData}
                fill="none"
                stroke={
                  isSelected
                    ? '#38bdf8'
                    : isBreached || edge.status === 'down'
                    ? '#EF4444'
                    : isRunning
                    ? '#8B5CF6'
                    : '#374151'
                }
                strokeWidth={isSelected ? '3' : isBreached ? '2.5' : '2'}
                strokeDasharray={isBreached || edge.status === 'down' ? '6,4' : undefined}
                className={isBreached ? 'animate-pulse' : ''}
              />
              {isRunning && (
                <circle r="3" fill={isBreached || edge.status === 'down' ? '#EF4444' : '#8B5CF6'}>
                  <animateMotion path={pathData} dur="1.2s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}

        {/* Dynamic Wire Draft */}
        {wireDraft && (() => {
          const sNode = topology.nodes.find((n) => n.id === wireDraft.sourceNodeId);
          if (!sNode) return null;
          const startCoords = getAnchorCoords(sNode, wireDraft.sourceAnchor);
          return (
            <line
              x1={startCoords.x}
              y1={startCoords.y}
              x2={wireDraft.currentX}
              y2={wireDraft.currentY}
              stroke="#06b6d4"
              strokeWidth="2.5"
              strokeDasharray="4,4"
              className="animate-pulse"
            />
          );
        })()}
      </svg>

      {/* Interactive Node Elements */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0'
        }}
      >
        {topology.nodes.map((node) => {
          const Icon = getNodeIcon(node.type);
          const isSelected = selectedNodeId === node.id;
          const isBreached = node.status === 'breached';
          const isBlocked = node.status === 'blocked';
          const isPoweredOff = node.power_state === 'stopped';
          const isPaused = node.power_state === 'paused';
          const isStarting = node.power_state === 'starting';

          let statusBorder = 'border-[#374151]';
          let statusGlow = '';
          if (isSelected) {
            statusBorder = 'border-cyan-400 ring-2 ring-cyan-500/30';
          } else if (isBreached) {
            statusBorder = 'border-[#EF4444]';
            statusGlow = 'shadow-[0_0_15px_rgba(239,68,68,0.4)]';
          } else if (isBlocked) {
            statusBorder = 'border-[#F59E0B]';
            statusGlow = 'shadow-[0_0_10px_rgba(245,158,11,0.25)]';
          }

          const powerOpacity = isPoweredOff ? 'opacity-50 grayscale' : '';

          return (
            <div
              key={node.id}
              onMouseDown={(e) => handleNodeMouseDown(e, node)}
              onDoubleClick={(e) => {
                e.stopPropagation();
                onInspectNode?.(node);
              }}
              className={`absolute w-44 h-[76px] rounded-lg bg-[#1F2937]/95 border backdrop-blur p-2 flex flex-col justify-between pointer-events-auto cursor-grab active:cursor-grabbing transition-all ${statusBorder} ${statusGlow} ${powerOpacity}`}
              style={{
                left: `${node.x}px`,
                top: `${node.y}px`
              }}
              title="Click to select, double-click to inspect virtual hardware & power"
            >
              {/* Port Anchors for Wiring (Top, Right, Bottom, Left) */}
              <div
                onMouseDown={(e) => handleAnchorMouseDown(e, node, 'top')}
                className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-800 hover:bg-cyan-400 border border-slate-600 rounded-full cursor-pointer z-10 transition-colors"
                title="Port 1 (Click &amp; Drag Wire)"
              />
              <div
                onMouseDown={(e) => handleAnchorMouseDown(e, node, 'right')}
                className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-3 h-3 bg-slate-800 hover:bg-cyan-400 border border-slate-600 rounded-full cursor-pointer z-10 transition-colors"
                title="Port 2 (Click &amp; Drag Wire)"
              />
              <div
                onMouseDown={(e) => handleAnchorMouseDown(e, node, 'bottom')}
                className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-800 hover:bg-cyan-400 border border-slate-600 rounded-full cursor-pointer z-10 transition-colors"
                title="Port 3 (Click &amp; Drag Wire)"
              />
              <div
                onMouseDown={(e) => handleAnchorMouseDown(e, node, 'left')}
                className="absolute top-1/2 -left-1.5 -translate-y-1/2 w-3 h-3 bg-slate-800 hover:bg-cyan-400 border border-slate-600 rounded-full cursor-pointer z-10 transition-colors"
                title="Port 4 (Click &amp; Drag Wire)"
              />

              {/* Node Card Header: Icon, Name & Inspect Action */}
              <div className="flex items-center gap-1.5">
                <div
                  className={`p-1 rounded-md shrink-0 ${
                    isBreached
                      ? 'bg-rose-950 text-rose-400 border border-rose-800'
                      : isBlocked
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-slate-950 text-cyan-400 border border-slate-800'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-slate-200 truncate font-mono flex items-center justify-between">
                    <span className="truncate">{node.name}</span>
                    {onInspectNode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onInspectNode(node);
                        }}
                        className="text-slate-500 hover:text-cyan-400 p-0.5 rounded hover:bg-slate-800 transition-colors cursor-pointer shrink-0 ml-1"
                        title="Configure Hardware & Power"
                      >
                        <Sliders className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono truncate">
                    {/* Power LED Indicator */}
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${
                        isPoweredOff
                          ? 'bg-slate-600'
                          : isPaused
                          ? 'bg-amber-400'
                          : isStarting
                          ? 'bg-sky-400 animate-ping'
                          : 'bg-[#10B981] shadow-[0_0_6px_#10B981]'
                      }`}
                      title={`Power State: ${node.power_state || 'running'}`}
                    />
                    <span className="truncate">{node.ip_address}</span>
                  </div>
                </div>
              </div>

              {/* Node Footer: Vendor / Hardware Spec & Operational Status */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[9px] font-mono">
                <div className="flex items-center gap-1 text-slate-400 truncate max-w-[100px]">
                  <span className="uppercase truncate">{node.vendor || node.type}</span>
                  {node.hardware && (
                    <span className="text-[8px] bg-slate-800/80 text-cyan-300 px-1 rounded border border-slate-700/60">
                      {node.hardware.vcpu_count}C/{Math.round(node.hardware.ram_mb / 1024)}G
                    </span>
                  )}
                </div>
                <span
                  className={`px-1 rounded font-bold uppercase ${
                    isPoweredOff
                      ? 'text-slate-400 bg-slate-800/90 border border-slate-700'
                      : isPaused
                      ? 'text-amber-400 bg-amber-950/80 border border-amber-900'
                      : isStarting
                      ? 'text-sky-300 bg-sky-950/80 border border-sky-800 animate-pulse'
                      : isBreached
                      ? 'text-rose-400 bg-rose-950/80 border border-rose-900'
                      : isBlocked
                      ? 'text-amber-400 bg-amber-950/80 border border-amber-900'
                      : 'text-emerald-400 bg-emerald-950/80 border border-emerald-900'
                  }`}
                >
                  {isPoweredOff ? 'STOPPED' : isPaused ? 'PAUSED' : isStarting ? 'BOOTING' : node.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
