import React, { useState } from 'react';
import { Package, Search, ExternalLink, ShieldCheck, Info, X, Layers, CheckCircle2 } from 'lucide-react';

interface VendorAddon {
  id: string;
  vendor: string;
  category: string;
  name: string;
  splunkbaseId: string;
  splunkbaseUrl: string;
  sourcetypes: string[];
  cimModels: string[];
  description: string;
}

const VENDOR_ADDONS: VendorAddon[] = [
  {
    id: 'cisco-catalyst',
    vendor: 'Cisco',
    category: 'Campus LAN & Wireless',
    name: 'Splunk Add-on for Cisco Catalyst Center (DNA-C)',
    splunkbaseId: '5580',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/5580',
    sourcetypes: ['cisco:catalyst:devicehealth', 'cisco:catalyst:clienthealth', 'cisco:catalyst:networkhealth', 'cisco:catalyst:issue', 'cisco:catalyst:rogue:*', 'cisco:catalyst:threat:*', 'cisco:dnac:compliance'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Alerts', 'Inventory'],
    description: 'Provides field extractions, CIM normalization, and operational dashboards for Cisco DNA-C / Catalyst Center telemetry and assurance events.'
  },
  {
    id: 'cisco-sdwan',
    vendor: 'Cisco',
    category: 'SD-WAN & Routing',
    name: 'Cisco SD-WAN Add-on for Splunk',
    splunkbaseId: '7538',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/7538',
    sourcetypes: ['cisco:sdwan:linkhealth', 'cisco:sdwan:sitehealth', 'cisco:sdwan:system:logs', 'cisco:sdwan:BGP-5-ADJCHANGE', 'cisco:sdwan:LINEPROTO-5-UPDOWN', 'cisco:sdwan:DMI-5-SYNC_COMPLETE'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Change Analysis', 'Performance'],
    description: 'Normalizes Cisco SD-WAN vManage, vSmart, and Edge router operational logs, link degradation alarms, and routing protocol state changes.'
  },
  {
    id: 'cisco-ise',
    vendor: 'Cisco',
    category: 'Identity & Access Control',
    name: 'Splunk Add-on for Cisco ISE',
    splunkbaseId: '1924',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/1924',
    sourcetypes: ['cisco:ise:syslog', 'cisco:ise:tacacs-policyset', 'cisco:ise:radius-authz-policy'],
    cimModels: ['Authentication', 'Change Analysis'],
    description: 'Extracts 802.1X, RADIUS, TACACS+ accounting, and posture assessment events into standard Splunk CIM Authentication data models.'
  },
  {
    id: 'cisco-sec-cloud',
    vendor: 'Cisco',
    category: 'Firewall & Threat Defense',
    name: 'Cisco Security Cloud Add-on / FTD Syslog',
    splunkbaseId: '6259',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/6259',
    sourcetypes: ['cisco:sfw:estreamer', 'cisco:sfw:policy', 'cisco:ftd:syslog'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Malware'],
    description: 'Ingests Cisco Secure Firewall (FTD) eStreamer connection events, intrusion events, and security intelligence rule hits.'
  },
  {
    id: 'cisco-duo',
    vendor: 'Cisco',
    category: 'MFA & Zero Trust',
    name: 'Duo Security Splunk Add-on',
    splunkbaseId: '3245',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/3245',
    sourcetypes: ['cisco:duo:authentication', 'cisco:duo:activity', 'cisco:duo:user', 'cisco:duo:administrator'],
    cimModels: ['Authentication', 'Change Analysis'],
    description: 'Parses Duo 2-Factor Authentication logs, enrollment activity, administrator audit trails, and telephony usage logs.'
  },
  {
    id: 'cisco-aci',
    vendor: 'Cisco',
    category: 'Data Center Fabric',
    name: 'Cisco ACI App & Add-on for Splunk',
    splunkbaseId: '1899',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/1899',
    sourcetypes: ['cisco:dc:aci:class', 'cisco:dc:aci:health', 'cisco:dc:aci:stats', 'cisco:dc:nexus9k:syslog'],
    cimModels: ['Network Sessions', 'Inventory', 'Performance'],
    description: 'Collects APIC health scores, fault instances, bridge domain status, and Nexus 9000 leaf/spine telemetry.'
  },
  {
    id: 'cisco-meraki',
    vendor: 'Cisco',
    category: 'Cloud Networking',
    name: 'Splunk Add-on for Cisco Meraki',
    splunkbaseId: '5619',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/5619',
    sourcetypes: ['meraki:devices', 'meraki:airmarshal', 'meraki:switchportsoverview', 'meraki:appliancesdwanstatuses'],
    cimModels: ['Network Traffic', 'Network Sessions', 'Alerts'],
    description: 'Extracts Meraki Dashboard API events, wireless air marshal rogue rogue containment, and MS switch port statuses.'
  },
  {
    id: 'cisco-1000eyes',
    vendor: 'Cisco',
    category: 'Synthetic Monitoring',
    name: 'Cisco ThousandEyes Add-on for Splunk',
    splunkbaseId: '5028',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/5028',
    sourcetypes: ['cisco:thousandeyes:event', 'cisco:thousandeyes:metric', 'thousandeyes_logs'],
    cimModels: ['Performance', 'Web', 'Alerts'],
    description: 'Maps ThousandEyes network latency, BGP route visualization, packet loss, and page load synthetic tests.'
  },
  {
    id: 'paloalto-panos',
    vendor: 'Palo Alto Networks',
    category: 'Next-Gen Firewall',
    name: 'Palo Alto Networks Add-on for Splunk',
    splunkbaseId: '2757',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2757',
    sourcetypes: ['pan:traffic', 'pan:threat', 'pan:system'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Malware', 'Alerts'],
    description: 'Normalizes PAN-OS traffic flows, threat prevention signatures, wildfire sandbox detections, and system alarms.'
  },
  {
    id: 'fortinet-fortigate',
    vendor: 'Fortinet',
    category: 'Next-Gen Firewall',
    name: 'Fortinet FortiGate Add-on for Splunk',
    splunkbaseId: '2800',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2800',
    sourcetypes: ['fortinet:fortigate:traffic', 'fortinet:fortigate:sdwan:alert'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Network Sessions'],
    description: 'Parses FortiOS traffic logs, SD-WAN health check SLAs, IPS detections, and antivirus events.'
  },
  {
    id: 'arista-eos',
    vendor: 'Arista Networks',
    category: 'Cloud Networking & Leaf-Spine',
    name: 'Arista Networks EOS Add-on for Splunk',
    splunkbaseId: '3350',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/3350',
    sourcetypes: ['arista:eos:syslog', 'arista:metrics:telemetry'],
    cimModels: ['Network Sessions', 'Performance'],
    description: 'Maps EOS Syslog, interface state changes, BGP peer transitions, and OpenConfig telemetry metrics.'
  },
  {
    id: 'juniper-junos',
    vendor: 'Juniper Networks',
    category: 'Routing & Switching',
    name: 'Splunk Add-on for Juniper',
    splunkbaseId: '2855',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2855',
    sourcetypes: ['juniper:syslog'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Alerts'],
    description: 'Normalizes Junos OS routing engine alarms, chassis management events, and BGP/OSPF protocol transitions.'
  },
  {
    id: 'sc4snmp',
    vendor: 'Splunk Community',
    category: 'SNMP Telemetry & Traps',
    name: 'Splunk Connect for SNMP (SC4SNMP)',
    splunkbaseId: 'SC4SNMP',
    splunkbaseUrl: 'https://splunk.github.io/splunk-connect-for-snmp/',
    sourcetypes: ['sc4snmp:metric', 'sc4snmp:event'],
    cimModels: ['Performance', 'Alerts', 'Inventory'],
    description: 'Processes high-frequency SNMP polling metrics and trap events with automated MIB translation and OID resolution.'
  },
  {
    id: 'nutanix-pc',
    vendor: 'Nutanix',
    category: 'Hyperconverged Infrastructure',
    name: 'Nutanix Prism Central Add-on for Splunk',
    splunkbaseId: '4432',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/4432',
    sourcetypes: ['nutanixpc_disk_performance', 'nutanixpc_vm_performance', 'nutanixpc_host_performance', 'nutanixpc_alerts'],
    cimModels: ['Performance', 'Inventory', 'Alerts'],
    description: 'Collects Nutanix AHV hypervisor metrics, Prism Central storage pool IOPS, and cluster health alerts.'
  },
  {
    id: 'vmware-vsphere',
    vendor: 'VMware',
    category: 'Virtualization & Compute',
    name: 'Splunk Add-on for VMware',
    splunkbaseId: '3215',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/3215',
    sourcetypes: ['vmware:esx:perf', 'vmware:inv', 'vmware:taskevent'],
    cimModels: ['Performance', 'Inventory', 'Change Analysis'],
    description: 'Extracts vCenter host/cluster performance counters, virtual machine topologies, and task/event records.'
  }
];

interface VendorAddonsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VendorAddonsModal: React.FC<VendorAddonsModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  if (!isOpen) return null;

  const categories = ['All', ...Array.from(new Set(VENDOR_ADDONS.map(a => a.category)))];

  const filteredAddons = VENDOR_ADDONS.filter(addon => {
    const matchesSearch = 
      addon.vendor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      addon.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      addon.sourcetypes.some(st => st.toLowerCase().includes(searchTerm.toLowerCase())) ||
      addon.category.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = selectedCategory === 'All' || addon.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-[#0f172a] border border-slate-700 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden text-slate-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0b0f19]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400">
              <Package className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Splunk Vendor Add-on (TA) Directory</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Cloud Vetted Architecture
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Official Splunk Technology Add-on mappings for simulated vendor sourcetypes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Architectural Note Banner */}
        <div className="px-6 py-3 bg-blue-950/40 border-b border-blue-900/40 flex items-start gap-3 text-xs text-blue-200">
          <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-blue-300">Why are third-party TAs not bundled in NetSpout?</span>
            <p className="mt-0.5 text-slate-300 leading-relaxed">
              NetSpout purposefully generates <b>100% schema-compliant raw and structured telemetry</b> matching official vendor formats. Bundling 20+ external TAs directly would inflate the app package from ~5MB to multiple gigabytes, cause severe dependency drift, and violate <b>Splunk Cloud AppInspect</b> vetting policies. Simply install the recommended vendor TA on your Search Heads or Indexers for automated CIM field extractions.
            </p>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="p-6 pb-2 flex flex-col md:flex-row gap-3 items-center justify-between border-b border-slate-800/80 bg-slate-900/40">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search vendor, sourcetype, or CIM model..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder-slate-500"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1">
            {categories.slice(0, 5).map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors shrink-0 ${
                  selectedCategory === cat
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Addon Catalog Cards */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredAddons.map((addon) => (
            <div
              key={addon.id}
              className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 flex flex-col justify-between hover:border-slate-700 transition-all hover:bg-slate-900 shadow-sm group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div>
                    <span className="text-[10px] font-semibold text-blue-400 tracking-wider uppercase">
                      {addon.vendor} • {addon.category}
                    </span>
                    <h3 className="text-sm font-bold text-slate-100 group-hover:text-blue-300 transition-colors">
                      {addon.name}
                    </h3>
                  </div>
                  <a
                    href={addon.splunkbaseUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-md transition-colors shrink-0"
                    title="View on Splunkbase"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed mb-3">
                  {addon.description}
                </p>

                {/* Sourcetypes list */}
                <div className="mb-2.5">
                  <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1 mb-1">
                    <Layers className="w-3 h-3 text-slate-400" />
                    Target Sourcetypes ({addon.sourcetypes.length}):
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {addon.sourcetypes.slice(0, 4).map((st) => (
                      <span
                        key={st}
                        className="px-1.5 py-0.5 bg-slate-950 border border-slate-800 rounded text-[10px] font-mono text-emerald-400"
                      >
                        {st}
                      </span>
                    ))}
                    {addon.sourcetypes.length > 4 && (
                      <span className="px-1 py-0.5 text-[10px] text-slate-500">
                        +{addon.sourcetypes.length - 4} more
                      </span>
                    )}
                  </div>
                </div>

                {/* CIM Data Models */}
                <div>
                  <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1 mb-1">
                    <CheckCircle2 className="w-3 h-3 text-blue-400" />
                    CIM Models:
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {addon.cimModels.map((cim) => (
                      <span
                        key={cim}
                        className="px-1.5 py-0.5 bg-blue-950/50 border border-blue-900/50 rounded text-[10px] text-blue-300"
                      >
                        {cim}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                <span className="text-slate-500 font-mono">
                  App ID: <span className="text-slate-300">{addon.splunkbaseId}</span>
                </span>
                <a
                  href={addon.splunkbaseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 font-medium transition-colors"
                >
                  Splunkbase <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}

          {filteredAddons.length === 0 && (
            <div className="col-span-2 text-center py-12 text-slate-500">
              <Package className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No vendor add-ons matched your query.</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-[#0b0f19] flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="text-slate-200 font-semibold">{filteredAddons.length}</span> of {VENDOR_ADDONS.length} recommended Technology Add-ons
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors"
          >
            Close Guide
          </button>
        </div>

      </div>
    </div>
  );
};
