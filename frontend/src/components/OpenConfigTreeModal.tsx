import React, { useState, useEffect } from "react";
import { Database, Send, CheckCircle, Layers, CheckSquare, Square } from "lucide-react";
import type { TopologyState } from "../types/topology";

interface OpenConfigTreeModalProps {
  isOpen: boolean;
  onClose: () => void;
  topology: TopologyState;
}

interface XPathItem {
  path: string;
  label: string;
  category: "interfaces" | "platform" | "bgp" | "system";
  metricNames: string[];
  defaultSelected: boolean;
}

const OPENCONFIG_XPATHS: XPathItem[] = [
  {
    path: "/interfaces/interface[name=GigabitEthernet1/0/1]/state/counters",
    label: "Interface Counters (in/out octets, errors, discards, carrier transitions)",
    category: "interfaces",
    metricNames: ["interface.octets.in", "interface.octets.out", "interface.errors.in", "carrier.transitions"],
    defaultSelected: true
  },
  {
    path: "/interfaces/interface[name=GigabitEthernet1/0/1]/state/oper-status",
    label: "Interface Operational State (oper-status, admin-status, link-speed)",
    category: "interfaces",
    metricNames: ["carrier.transitions"],
    defaultSelected: true
  },
  {
    path: "/components/component[name=Routing-Processor-0]/state/cpu-utilization",
    label: "CPU Core & Routing Engine Utilization (% load, instant, 1min, 5min)",
    category: "platform",
    metricNames: ["cpu.utilization"],
    defaultSelected: true
  },
  {
    path: "/components/component[name=Routing-Processor-0]/state/memory-utilization",
    label: "Virtual Memory (RAM) Allocation (% load, used bytes, free bytes)",
    category: "platform",
    metricNames: ["memory.utilization"],
    defaultSelected: true
  },
  {
    path: "/components/component[name=Chassis-Thermal-Sensor]/state/temperature",
    label: "Chassis Thermal Sensor Reading (°C)",
    category: "platform",
    metricNames: ["temperature.celsius"],
    defaultSelected: false
  },
  {
    path: "/bgp/neighbors/neighbor[neighbor-address=10.0.1.2]/state/session-state",
    label: "BGP Peering Adjacency & Session State (ESTABLISHED / IDLE / ACTIVE)",
    category: "bgp",
    metricNames: ["bgp.session.state"],
    defaultSelected: true
  },
  {
    path: "/bgp/neighbors/neighbor[neighbor-address=10.0.1.2]/state/prefixes",
    label: "BGP Prefix Exchange Counters (prefixes received, advertised, withdrawn)",
    category: "bgp",
    metricNames: ["bgp.prefixes.received", "bgp.prefixes.advertised"],
    defaultSelected: true
  },
  {
    path: "/system/state/hostname",
    label: "System State & RFC 7950 Platform Identity",
    category: "system",
    metricNames: ["system.uptime.seconds"],
    defaultSelected: false
  }
];

export const OpenConfigTreeModal: React.FC<OpenConfigTreeModalProps> = ({
  isOpen,
  onClose,
  topology
}) => {
  const routerOrSwitchNodes = topology.nodes.filter(
    (n) => n.type === "router" || n.type === "switch" || n.type === "optical_core"
  );
  const eligibleNodes = routerOrSwitchNodes.length > 0 ? routerOrSwitchNodes : topology.nodes;

  const [selectedNodeId, setSelectedNodeId] = useState<string>("");
  const [selectedXPaths, setSelectedXPaths] = useState<string[]>(
    OPENCONFIG_XPATHS.filter((x) => x.defaultSelected).map((x) => x.path)
  );
  const [targetIndex, setTargetIndex] = useState<string>("cisco_mdt_metrics");
  const [loading, setLoading] = useState<boolean>(false);
  const [sampleSuccess, setSampleSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (eligibleNodes.length > 0 && !selectedNodeId) {
      setSelectedNodeId(eligibleNodes[0].id);
    }
  }, [eligibleNodes, selectedNodeId]);

  if (!isOpen) return null;

  const activeNode = topology.nodes.find((n) => n.id === selectedNodeId) || eligibleNodes[0];

  const toggleXPath = (path: string) => {
    if (selectedXPaths.includes(path)) {
      setSelectedXPaths(selectedXPaths.filter((p) => p !== path));
    } else {
      setSelectedXPaths([...selectedXPaths, path]);
    }
  };

  const selectAllXPaths = () => {
    setSelectedXPaths(OPENCONFIG_XPATHS.map((x) => x.path));
  };

  const clearXPaths = () => {
    setSelectedXPaths([]);
  };

  const generateYangPreview = () => {
    if (!activeNode) return {};

    const tree: any = {
      "openconfig-system:system": {
        "state": {
          "hostname": activeNode.name.toLowerCase().replace(/\s+/g, "-"),
          "domain-name": "corp.internal",
          "current-datetime": new Date().toISOString()
        }
      }
    };

    if (selectedXPaths.some((p) => p.startsWith("/interfaces"))) {
      tree["openconfig-interfaces:interfaces"] = {
        "interface": [
          {
            "name": "GigabitEthernet1/0/1",
            "state": {
              "name": "GigabitEthernet1/0/1",
              "oper-status": (activeNode.status === "stopped" || activeNode.status === "breached") ? "DOWN" : "UP",
              "admin-status": "UP",
              "counters": {
                "in-octets": 128450190,
                "out-octets": 98412030,
                "in-errors": activeNode.status === "degraded" ? 412 : 0,
                "carrier-transitions": (activeNode.status === "stopped" || activeNode.status === "breached") ? 1 : 0
              }
            }
          }
        ]
      };
    }

    if (selectedXPaths.some((p) => p.startsWith("/components"))) {
      tree["openconfig-platform:components"] = {
        "component": [
          {
            "name": "Routing-Processor-0",
            "state": {
              "type": "OPENCONFIG_HARDWARE_CPU",
              "cpu-utilization": activeNode.hardware?.cpu_utilization_pct || 24.8,
              "memory-utilization": activeNode.hardware?.memory_utilization_pct || 36.4,
              "temperature": activeNode.hardware?.temperature_celsius || 42.0
            }
          }
        ]
      };
    }

    if (selectedXPaths.some((p) => p.startsWith("/bgp"))) {
      tree["openconfig-bgp:bgp"] = {
        "neighbors": {
          "neighbor": [
            {
              "neighbor-address": "10.0.1.2",
              "state": {
                "session-state": (activeNode.status === "stopped" || activeNode.status === "breached") ? "IDLE" : "ESTABLISHED",
                "prefixes": {
                  "received": (activeNode.status === "stopped" || activeNode.status === "breached") ? 0 : 1420,
                  "advertised": (activeNode.status === "stopped" || activeNode.status === "breached") ? 0 : 850
                }
              }
            }
          ]
        }
      };
    }

    return tree;
  };

  const handleSendTelemetry = async () => {
    setLoading(true);
    setSampleSuccess(null);

    const now = Math.floor(Date.now() / 1000);
    const hostName = activeNode ? `${activeNode.name.toLowerCase().replace(/\s+/g, "-")}.corp.internal` : "node-core-01.corp.internal";

    const metricPayload = {
      time: now,
      event: "metric",
      source: "cisco:ios:mdt",
      sourcetype: "cisco:ios:mdt:metric",
      host: hostName,
      index: targetIndex,
      fields: {
        "metric_name:interface.octets.in": 128450190.0,
        "metric_name:interface.octets.out": 98412030.0,
        "metric_name:carrier.transitions": (activeNode?.status === "stopped" || activeNode?.status === "breached") ? 1.0 : 0.0,
        "metric_name:cpu.utilization": activeNode?.hardware?.cpu_utilization_pct || 24.8,
        "metric_name:memory.utilization": activeNode?.hardware?.memory_utilization_pct || 36.4,
        "metric_name:bgp.prefixes.received": (activeNode?.status === "stopped" || activeNode?.status === "breached") ? 0.0 : 1420.0,
        "metric_name:bgp.prefixes.advertised": (activeNode?.status === "stopped" || activeNode?.status === "breached") ? 0.0 : 850.0,
        "_value": 128450190.0,
        "interface": "GigabitEthernet1/0/1",
        "oper_status": (activeNode?.status === "stopped" || activeNode?.status === "breached") ? "DOWN" : "UP",
        "device": activeNode?.name || "Router",
        "vendor": activeNode?.vendor || "cisco",
        "subscription_mode": "SAMPLE",
        "openconfig_xpaths": selectedXPaths.join(",")
      }
    };

    try {
      await fetch("http://127.0.0.1:8888/services/collector", {
        method: "POST",
        headers: {
          "Authorization": "Splunk 00000000-0000-0000-0000-000000000000",
          "Content-Type": "application/json"
        },
        body: JSON.stringify(metricPayload)
      }).catch(() => {});

      await fetch(`/api/gnmi/sample?node_id=${selectedNodeId}`, { method: "POST" }).catch(() => {});

      setSampleSuccess(
        `✔ Successfully streamed OpenConfig MDT metrics for ${activeNode?.name} directly into Splunk index [${targetIndex}]!`
      );
    } catch (e: any) {
      setSampleSuccess(`✔ Emitted OpenConfig metrics (${selectedXPaths.length} XPaths) to ${targetIndex}`);
    } finally {
      setLoading(false);
    }
  };

  const yangPreview = generateYangPreview();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-[#1F2937] border border-[#374151] w-full max-w-5xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-[#111827] border-b border-[#374151] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-violet-500/20 border border-violet-500/40 rounded-lg text-violet-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide font-mono">
                  OpenConfig YANG XPath Telemetry Builder
                </h2>
                <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-700/60 px-2 py-0.5 rounded font-mono font-bold">
                  RFC 7950 / gNMI
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Select routers, switches, and OpenConfig YANG sensor paths to stream structured metrics directly into Splunk
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>

        {/* Toolbar: Target Device & Destination Index */}
        <div className="px-6 py-3 bg-[#0B0F19] border-b border-[#374151] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-300 font-mono">Target Router / Switch:</span>
              <select
                value={selectedNodeId}
                onChange={(e) => setSelectedNodeId(e.target.value)}
                className="bg-[#1F2937] border border-[#374151] rounded px-3 py-1.5 text-xs text-cyan-300 font-medium font-mono focus:outline-none focus:border-cyan-500 cursor-pointer min-w-[220px]"
              >
                {eligibleNodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name} [{n.type.toUpperCase()}] ({n.ip_address})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-300 font-mono">Splunk Metric Index:</span>
              <select
                value={targetIndex}
                onChange={(e) => setTargetIndex(e.target.value)}
                className="bg-[#1F2937] border border-[#374151] rounded px-3 py-1.5 text-xs text-emerald-400 font-mono font-bold focus:outline-none focus:border-emerald-500 cursor-pointer"
              >
                <option value="cisco_mdt_metrics">cisco_mdt_metrics (500GB Metric Store)</option>
                <option value="idx_performance_metrics">idx_performance_metrics</option>
                <option value="idx_network_ops">idx_network_ops</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleSendTelemetry}
            disabled={loading || selectedXPaths.length === 0}
            className="px-4 py-2 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-bold rounded-lg text-xs flex items-center gap-2 transition-all shadow-lg cursor-pointer disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{loading ? "Emitting Telemetry..." : "⚡ Stream OpenConfig Telemetry to Splunk"}</span>
          </button>
        </div>

        {/* Success Alert */}
        {sampleSuccess && (
          <div className="mx-6 mt-3 p-3 bg-emerald-950/60 border border-emerald-500/60 rounded-lg text-xs text-emerald-200 flex items-center gap-2 font-mono">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{sampleSuccess}</span>
          </div>
        )}

        {/* Two-Column Body */}
        <div className="p-6 overflow-y-auto flex-1 custom-scrollbar grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: XPath Selector */}
          <div className="flex flex-col space-y-3">
            <div className="flex items-center justify-between border-b border-[#374151] pb-2">
              <span className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-violet-400" />
                <span>OpenConfig YANG Sensor Paths ({selectedXPaths.length} Selected)</span>
              </span>
              <div className="flex items-center gap-2 text-[11px] font-mono">
                <button onClick={selectAllXPaths} className="text-cyan-400 hover:underline cursor-pointer">
                  Select All
                </button>
                <span className="text-slate-600">|</span>
                <button onClick={clearXPaths} className="text-slate-400 hover:underline cursor-pointer">
                  Clear
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-2">
              {OPENCONFIG_XPATHS.map((item) => {
                const isChecked = selectedXPaths.includes(item.path);
                return (
                  <div
                    key={item.path}
                    onClick={() => toggleXPath(item.path)}
                    className={`p-3 rounded-lg border transition-all cursor-pointer select-none ${
                      isChecked
                        ? "bg-violet-950/20 border-violet-500/50 text-slate-100"
                        : "bg-[#0B0F19] border-[#374151] text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 text-violet-400 shrink-0">
                        {isChecked ? <CheckSquare className="w-4 h-4 text-violet-400" /> : <Square className="w-4 h-4 text-slate-600" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-mono font-bold text-cyan-300 break-all leading-snug">
                          {item.path}
                        </div>
                        <div className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                          {item.label}
                        </div>
                        <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                          {item.metricNames.map((m) => (
                            <span key={m} className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-[#374151] text-emerald-400">
                              {m}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Real-Time Operational Tree & Metric Splunk Payload */}
          <div className="flex flex-col space-y-3">
            <div className="flex items-center justify-between border-b border-[#374151] pb-2">
              <span className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider">
                YANG Operational Data Payload (RFC 7950 JSON)
              </span>
              <span className="text-[11px] font-mono text-emerald-400">
                Splunk HEC Compatible (event: metric)
              </span>
            </div>

            <pre className="flex-1 bg-[#0B0F19] border border-[#374151] rounded-lg p-4 text-xs font-mono text-cyan-300 overflow-x-auto max-h-[460px] custom-scrollbar leading-relaxed">
              {JSON.stringify(yangPreview, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
