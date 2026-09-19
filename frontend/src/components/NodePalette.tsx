import React from 'react';
import {
  ShieldAlert,
  Router,
  Network,
  GitFork,
  Server,
  Database,
  Globe,
  Radio,
  Cloud,
  Cpu,
  Trash2,
  Info,
  Sliders,
  Sparkles
} from 'lucide-react';
import type { Node, NodeType, ScenarioType, EcosystemMode } from '../types/topology';
import { SCENARIOS } from '../presets/defaultTopologies';

export interface PaletteItem {
  type: NodeType;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  badge: string;
  desc: string;
  defaultVendor: string;
  defaultSourcetype: string;
  defaultIp: string;
  category: string;
  ecosystem: EcosystemMode;
}

export const PALETTE_ITEMS: PaletteItem[] = [
  // ==========================================
  // PURE CISCO ARCHITECTURE ITEMS
  // ==========================================
  {
    type: 'switch',
    name: 'Catalyst 9300 Switch',
    icon: Network,
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/40 hover:border-sky-400',
    badge: 'CATALYST',
    desc: 'Campus Core/Access L2/3 Switch',
    defaultVendor: 'cisco_catalyst',
    defaultSourcetype: 'cisco:ios:syslog',
    defaultIp: '10.10.20.1',
    category: 'Campus & Wireless',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'wireless_ap',
    name: 'Catalyst 9120 AP',
    icon: Radio,
    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/40 hover:border-cyan-400',
    badge: 'AIR-MARSHAL',
    desc: 'Wi-Fi 6 AP with CleanAir Rogue Detection',
    defaultVendor: 'cisco_catalyst',
    defaultSourcetype: 'cisco:catalyst:rogue:threat_details',
    defaultIp: '10.10.20.5',
    category: 'Campus & Wireless',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'switch',
    name: 'Catalyst 9800 WLC',
    icon: Network,
    color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/40 hover:border-indigo-400',
    badge: 'WIRELESS',
    desc: 'Enterprise Wireless Controller',
    defaultVendor: 'cisco_catalyst',
    defaultSourcetype: 'cisco:catalyst:security:events',
    defaultIp: '10.10.1.10',
    category: 'Campus & Wireless',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'firewall',
    name: 'Cisco ISE PSN',
    icon: ShieldAlert,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/40 hover:border-emerald-400',
    badge: 'IDENTITY',
    desc: '802.1X TrustSec & Quarantine Node',
    defaultVendor: 'cisco_ise',
    defaultSourcetype: 'cisco:ise:syslog',
    defaultIp: '10.10.1.25',
    category: 'Security & Identity',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'firewall',
    name: 'Cisco Secure FTD / ASA',
    icon: ShieldAlert,
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/40 hover:border-rose-400',
    badge: 'NGFW',
    desc: 'Perimeter Threat Defense Firewall',
    defaultVendor: 'cisco_asa',
    defaultSourcetype: 'cisco:asa',
    defaultIp: '198.51.100.1',
    category: 'Security & Identity',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'router',
    name: 'Catalyst 8300 / vEdge',
    icon: Router,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/40 hover:border-amber-400',
    badge: 'SD-WAN',
    desc: 'Edge Router with BFD SLA Tracking',
    defaultVendor: 'cisco_sdwan',
    defaultSourcetype: 'cisco:sdwan:linkhealth',
    defaultIp: '172.16.1.1',
    category: 'WAN & Routing',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'client_external',
    name: 'ThousandEyes Agent',
    icon: Globe,
    color: 'text-violet-400 bg-violet-500/10 border-violet-500/40 hover:border-violet-400',
    badge: 'SYNTHETIC',
    desc: 'Active Network Path Synthetics',
    defaultVendor: 'cisco_thousandeyes',
    defaultSourcetype: 'cisco:thousandeyes:metric',
    defaultIp: '172.16.1.50',
    category: 'WAN & Routing',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'switch',
    name: 'Nexus 9336 Leaf',
    icon: Cpu,
    color: 'text-teal-400 bg-teal-500/10 border-teal-500/40 hover:border-teal-400',
    badge: 'ACI LEAF',
    desc: 'Cloud Scale ASIC Leaf Switch',
    defaultVendor: 'cisco_nexus',
    defaultSourcetype: 'cisco:dc:nexus9k:syslog',
    defaultIp: '10.255.0.11',
    category: 'Data Center & Fabric',
    ecosystem: 'pure_cisco'
  },
  {
    type: 'switch',
    name: 'Nexus 9508 Spine',
    icon: Cpu,
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/40 hover:border-blue-400',
    badge: 'ACI SPINE',
    desc: 'Modular 400G Fabric Spine',
    defaultVendor: 'cisco_nexus',
    defaultSourcetype: 'cisco:dc:aci:health',
    defaultIp: '10.255.0.1',
    category: 'Data Center & Fabric',
    ecosystem: 'pure_cisco'
  },

  // ==========================================
  // MIXED-VENDOR ENTERPRISE INFRASTRUCTURE ITEMS
  // ==========================================
  {
    type: 'wireless_ap',
    name: 'Meraki MR56 AP',
    icon: Radio,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/40 hover:border-emerald-400',
    badge: 'MERAKI',
    desc: 'Cloud-managed Wi-Fi 6 with Air Marshal',
    defaultVendor: 'meraki',
    defaultSourcetype: 'meraki:assurancealerts',
    defaultIp: '10.128.0.55',
    category: 'Edge & SASE',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'sase_proxy',
    name: 'Zscaler ZIA Cloud Edge',
    icon: Cloud,
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/40 hover:border-sky-400',
    badge: 'ZIA PROXY',
    desc: 'Secure Internet Access Cloud Proxy',
    defaultVendor: 'zscaler',
    defaultSourcetype: 'zscaler:zia',
    defaultIp: '165.225.10.1',
    category: 'Edge & SASE',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'firewall',
    name: 'Palo Alto PA-440 NGFW',
    icon: ShieldAlert,
    color: 'text-orange-400 bg-orange-500/10 border-orange-500/40 hover:border-orange-400',
    badge: 'PAN-OS',
    desc: 'Next-Gen Firewall with App-ID / Threat',
    defaultVendor: 'palo_alto',
    defaultSourcetype: 'pan:threat',
    defaultIp: '10.128.1.1',
    category: 'Firewalls & Security',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'firewall',
    name: 'Fortinet FortiGate',
    icon: ShieldAlert,
    color: 'text-red-400 bg-red-500/10 border-red-500/40 hover:border-red-400',
    badge: 'FORTIOS',
    desc: 'High-Throughput Threat Protection',
    defaultVendor: 'fortinet',
    defaultSourcetype: 'fortinet:fortigate',
    defaultIp: '10.128.1.2',
    category: 'Firewalls & Security',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'optical_core',
    name: 'Nokia 7750 SR-OS Core',
    icon: Router,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/40 hover:border-purple-400',
    badge: 'SR-OS',
    desc: 'Carrier Grade DWDM / MPLS Optical Core',
    defaultVendor: 'nokia_sros',
    defaultSourcetype: 'nokia:sros:syslog',
    defaultIp: '10.200.0.1',
    category: 'Backbone & Routing',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'router',
    name: 'Juniper MX960 PE',
    icon: Router,
    color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/40 hover:border-indigo-400',
    badge: 'JUNOS',
    desc: 'Carrier Ethernet Provider Edge with RSVP-TE',
    defaultVendor: 'juniper_junos',
    defaultSourcetype: 'juniper:junos',
    defaultIp: '10.200.0.2',
    category: 'Backbone & Routing',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'switch',
    name: 'Arista 7280R Leaf',
    icon: Network,
    color: 'text-teal-400 bg-teal-500/10 border-teal-500/40 hover:border-teal-400',
    badge: 'EOS IPFIX',
    desc: 'Deep Buffer Routing Switch with Flow IPFIX',
    defaultVendor: 'arista_eos',
    defaultSourcetype: 'arista:flow:ipfix',
    defaultIp: '10.200.0.3',
    category: 'Backbone & Routing',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'load_balancer',
    name: 'F5 BIG-IP LTM',
    icon: GitFork,
    color: 'text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/40 hover:border-fuchsia-400',
    badge: 'BIG-IP',
    desc: 'Local Traffic Manager Session Balancer',
    defaultVendor: 'f5',
    defaultSourcetype: 'f5:bigip:ltm',
    defaultIp: '10.0.1.5',
    category: 'Data Center & Compute',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'web_server',
    name: 'Nginx Web Cluster',
    icon: Server,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/40 hover:border-emerald-400',
    badge: 'NGINX',
    desc: 'High-Performance HTTP / Reverse Proxy',
    defaultVendor: 'nginx',
    defaultSourcetype: 'nginx:plus:kv',
    defaultIp: '10.0.1.10',
    category: 'Data Center & Compute',
    ecosystem: 'mixed_vendor'
  },
  {
    type: 'database',
    name: 'PostgreSQL Database',
    icon: Database,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/40 hover:border-amber-400',
    badge: 'DATA',
    desc: 'Production SQL Relational Backend',
    defaultVendor: 'postgresql',
    defaultSourcetype: 'postgresql:audit',
    defaultIp: '10.0.2.50',
    category: 'Data Center & Compute',
    ecosystem: 'mixed_vendor'
  }
];

interface NodePaletteProps {
  ecosystemMode: EcosystemMode;
  onAddNode: (type: NodeType, overrides?: Partial<Node>) => void;
  selectedNode: Node | null;
  onUpdateSelectedNode: (updated: Partial<Node>) => void;
  onDeleteSelectedNode: (nodeId: string) => void;
  activeScenario: ScenarioType;
}

export const NodePalette: React.FC<NodePaletteProps> = ({
  ecosystemMode,
  onAddNode,
  selectedNode,
  onUpdateSelectedNode,
  onDeleteSelectedNode,
  activeScenario
}) => {
  const scenarioDef = SCENARIOS.find((s) => s.id === activeScenario) || SCENARIOS[0];

  const filteredItems = PALETTE_ITEMS.filter((item) => item.ecosystem === ecosystemMode);

  // Group items by category
  const categories = Array.from(new Set(filteredItems.map((item) => item.category)));

  const handleDragStart = (e: React.DragEvent, item: PaletteItem) => {
    e.dataTransfer.setData('application/node-type', item.type);
    e.dataTransfer.setData('application/node-vendor', item.defaultVendor);
    e.dataTransfer.setData('application/node-sourcetype', item.defaultSourcetype);
    e.dataTransfer.setData('application/node-name', item.name);
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <aside className="w-68 bg-[#1F2937] border-r border-[#374151] flex flex-col h-full overflow-hidden shrink-0 select-none z-20">
      {/* Node Palette Header */}
      <div className="p-3 border-b border-[#374151] bg-[#1F2937]">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-mono flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Infrastructure Palette</span>
          </h2>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#0B0F19] border border-[#374151] text-cyan-400">
            {ecosystemMode === 'pure_cisco' ? 'CISCO ONLY' : 'MULTI-VENDOR'}
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-0.5">
          Drag components onto canvas or click to add
        </p>
      </div>

      {/* Categorized Palette Items List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-3">
        {categories.map((cat) => {
          const items = filteredItems.filter((i) => i.category === cat);
          return (
            <div key={cat} className="space-y-1.5">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold px-1 flex items-center gap-1.5">
                <span className="w-1 h-3 bg-cyan-500 rounded-sm inline-block" />
                <span>{cat}</span>
              </div>
              <div className="space-y-1.5">
                {items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.name}
                      draggable
                      onDragStart={(e) => handleDragStart(e, item)}
                      onClick={() =>
                        onAddNode(item.type, {
                          name: item.name,
                          vendor: item.defaultVendor,
                          sourcetype: item.defaultSourcetype,
                          ip_address: item.defaultIp
                        })
                      }
                      className={`p-2 rounded-lg border transition-all cursor-grab active:cursor-grabbing flex items-center gap-2.5 group shadow-sm ${item.color}`}
                      title="Click or Drag onto Canvas"
                    >
                      <div className="p-1.5 rounded-md bg-slate-950/80 border border-slate-800/80 group-hover:scale-105 transition-transform">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 truncate">
                            {item.name}
                          </span>
                          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[#0B0F19] border border-[#374151] text-slate-400">
                            {item.badge}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-400 truncate mt-0.5">
                          {item.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Node Properties Inspector */}
      {selectedNode ? (
        <div className="p-3 bg-slate-900/90 border-t border-slate-800 shrink-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5" />
              <span>Node Inspector</span>
            </h3>
            <button
              onClick={() => onDeleteSelectedNode(selectedNode.id)}
              className="text-slate-400 hover:text-red-400 p-1 rounded hover:bg-slate-800 transition-colors cursor-pointer"
              title="Delete this node (or press Delete key)"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 text-[11px] font-mono">
            <div>
              <label className="text-[10px] text-slate-500 uppercase block">Name</label>
              <input
                type="text"
                value={selectedNode.name}
                onChange={(e) => onUpdateSelectedNode({ name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 uppercase block">IP Address</label>
              <input
                type="text"
                value={selectedNode.ip_address}
                onChange={(e) => onUpdateSelectedNode({ ip_address: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 uppercase block">Vendor & Sourcetype</label>
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={selectedNode.vendor}
                  onChange={(e) => onUpdateSelectedNode({ vendor: e.target.value })}
                  placeholder="vendor"
                  className="w-1/2 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-cyan-500"
                />
                <input
                  type="text"
                  value={selectedNode.sourcetype || ''}
                  onChange={(e) => onUpdateSelectedNode({ sourcetype: e.target.value })}
                  placeholder="sourcetype"
                  className="w-1/2 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-cyan-300 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
            <div>
              <label className="text-[10px] text-slate-500 uppercase block">Security Status</label>
              <select
                value={selectedNode.status}
                onChange={(e) => onUpdateSelectedNode({ status: e.target.value as any })}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="active">Active (Normal)</option>
                <option value="blocked">Blocked (Dropped)</option>
                <option value="breached">Breached (Compromised)</option>
                <option value="degraded">Degraded (Saturated)</option>
              </select>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3 bg-slate-900/60 border-t border-slate-800 shrink-0 text-center text-slate-500 text-[11px]">
          Click any node on canvas to inspect properties
        </div>
      )}

      {/* Active Scenario Security Summary Card */}
      <div className="p-3 bg-slate-950 border-t border-slate-800/80 text-[11px] font-mono">
        <div className="flex items-center gap-1.5 text-cyan-400 font-bold mb-1">
          <Info className="w-3.5 h-3.5" />
          <span>Active Scenario Defense Logic:</span>
        </div>
        <p className="text-slate-400 leading-relaxed text-[10px]">
          {scenarioDef.defenseMechanism}
        </p>
      </div>
    </aside>
  );
};

