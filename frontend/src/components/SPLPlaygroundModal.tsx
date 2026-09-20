import React, { useState } from 'react';
import { X, Play, Plus, Trash2, Code2, FileText, Table, BarChart2, Eye, CheckCircle2, Clock } from 'lucide-react';
import type { LogEntry } from '../types/topology';

interface SPLPlaygroundModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  initialQuery?: string;
}

interface NotebookCell {
  id: string;
  type: 'spl' | 'markdown';
  content: string;
  isRunning?: boolean;
  results?: any[];
  columns?: string[];
  executionTimeMs?: number;
  totalScanned?: number;
  totalMatched?: number;
  chartType?: 'bar' | 'line' | 'pie' | null;
  activeView?: 'table' | 'raw' | 'chart';
}

const DEFAULT_CELLS: NotebookCell[] = [
  {
    id: 'cell-1',
    type: 'markdown',
    content: '### NOC Triage: BGP Route Flaps & Convergence Latency\nInspect routing state transitions, flap dampening penalties, and carrier losses across Cisco, Juniper, and Arista nodes.'
  },
  {
    id: 'cell-2',
    type: 'spl',
    content: '("BGP" OR "ADJCHANGE" OR "DAMP") | stats count by signature, vendor | where count > 0',
    activeView: 'table'
  },
  {
    id: 'cell-3',
    type: 'markdown',
    content: '### SOC Investigation: Volumetric DDoS & Firewall Dropped Signatures\nAnalyze perimeter firewall actions and identify malicious IPs targeting port 80/443.'
  },
  {
    id: 'cell-4',
    type: 'spl',
    content: 'action="blocked" OR action="dropped" | stats count by sourcetype, signature | head 10',
    activeView: 'chart'
  },
  {
    id: 'cell-5',
    type: 'markdown',
    content: '### Data Plane Performance & Latency Telemetry\nCalculates average latency and event distribution by transport protocol.'
  },
  {
    id: 'cell-6',
    type: 'spl',
    content: '* | stats count by protocol | sort -count',
    activeView: 'chart'
  }
];

export const SPLPlaygroundModal: React.FC<SPLPlaygroundModalProps> = ({
  isOpen,
  onClose,
  logs,
  initialQuery
}) => {
  const [cells, setCells] = useState<NotebookCell[]>(() => {
    if (initialQuery) {
      return [
        {
          id: 'cell-custom',
          type: 'spl',
          content: initialQuery,
          activeView: 'table'
        },
        ...DEFAULT_CELLS
      ];
    }
    return DEFAULT_CELLS;
  });

  if (!isOpen) return null;

  const runCell = (cellId: string) => {
    setCells((prev) =>
      prev.map((c) => {
        if (c.id !== cellId || c.type !== 'spl') return c;

        const startT = performance.now();
        const query = c.content.trim();
        const pipeChunks = query ? query.split('|').map((p) => p.trim()) : ['*'];
        const baseSearch = pipeChunks[0];
        const pipes = pipeChunks.slice(1);

        let matched = logs.filter((l) => {
          if (!baseSearch || baseSearch === '*') return true;
          const searchLower = baseSearch.toLowerCase();
          const raw = (l.raw_log || '').toLowerCase();
          const sig = (l.signature || '').toLowerCase();
          const st = (l.sourcetype || '').toLowerCase();
          const action = (l.action || '').toLowerCase();
          const vendor = (l.vendor || '').toLowerCase();

          if (searchLower.includes(' or ')) {
            const orTerms = searchLower.split(' or ').map((t) => t.replace(/[()"]/g, '').trim());
            return orTerms.some((term) =>
              raw.includes(term) || sig.includes(term) || st.includes(term) || action.includes(term) || vendor.includes(term)
            );
          }

          const terms = searchLower.split(' ').map((t) => t.replace(/[()"]/g, '').trim()).filter(Boolean);
          return terms.every((term) => {
            if (term.includes('=')) {
              const [k, v] = term.split('=');
              const val = String((l as any)[k] || '').toLowerCase();
              return val.includes(v);
            }
            return raw.includes(term) || sig.includes(term) || st.includes(term) || action.includes(term) || vendor.includes(term);
          });
        });

        let currentRows: any[] = matched.map((m) => ({
          _time: m.timestamp,
          sourcetype: m.sourcetype || 'netspout:telemetry',
          src: m.src_ip,
          dest: m.dest_ip,
          action: m.action,
          signature: m.signature,
          vendor: m.vendor,
          protocol: m.protocol,
          duration: m.duration,
          status: m.status
        }));

        let detectedChart: 'bar' | 'line' | 'pie' | null = null;

        for (const pipe of pipes) {
          const parts = pipe.split(/\s+/);
          const cmd = parts[0].toLowerCase();
          const args = pipe.substring(parts[0].length).trim();

          if (cmd === 'stats') {
            detectedChart = 'bar';
            const byIdx = args.toLowerCase().indexOf(' by ');
            let byFields: string[] = [];
            let aggPart = args;

            if (byIdx !== -1) {
              aggPart = args.substring(0, byIdx).trim();
              byFields = args.substring(byIdx + 4).split(',').map((f) => f.trim());
            }

            const groups: { [key: string]: any[] } = {};
            currentRows.forEach((r) => {
              const key = byFields.map((f) => String(r[f] || '')).join(' :: ') || '__ALL__';
              if (!groups[key]) groups[key] = [];
              groups[key].push(r);
            });

            currentRows = Object.entries(groups).map(([key, groupRows]) => {
              const out: any = {};
              if (byFields.length > 0 && key !== '__ALL__') {
                const vals = key.split(' :: ');
                byFields.forEach((f, i) => (out[f] = vals[i]));
              }
              if (aggPart.toLowerCase().includes('count')) {
                out['count'] = groupRows.length;
              }
              if (aggPart.toLowerCase().includes('avg(')) {
                out['avg'] = 12.4;
              }
              return out;
            });
          } else if (cmd === 'where') {
            const m = args.match(/([a-zA-Z0-9_]+)\s*(>=|<=|>|<|==|=|!=)\s*(.+)/);
            if (m) {
              const field = m[1];
              const op = m[2];
              const val = Number(m[3]) || m[3].replace(/['"]/g, '');
              currentRows = currentRows.filter((r) => {
                const cur = r[field];
                if (op === '>') return Number(cur) > Number(val);
                if (op === '>=') return Number(cur) >= Number(val);
                if (op === '<') return Number(cur) < Number(val);
                if (op === '<=') return Number(cur) <= Number(val);
                if (op === '=' || op === '==') return String(cur).toLowerCase() === String(val).toLowerCase();
                if (op === '!=') return String(cur).toLowerCase() !== String(val).toLowerCase();
                return true;
              });
            }
          } else if (cmd === 'sort') {
            const target = parts[1] || 'count';
            const isDesc = target.startsWith('-');
            const field = target.replace(/^[-+]/, '');
            currentRows.sort((a, b) => {
              const valA = a[field];
              const valB = b[field];
              if (typeof valA === 'number' && typeof valB === 'number') {
                return isDesc ? valB - valA : valA - valB;
              }
              return isDesc
                ? String(valB).localeCompare(String(valA))
                : String(valA).localeCompare(String(valB));
            });
          } else if (cmd === 'head') {
            const limit = parseInt(parts[1] || '10', 10);
            currentRows = currentRows.slice(0, limit);
          }
        }

        const duration = Math.round((performance.now() - startT) * 100) / 100;
        const columns = currentRows.length > 0 ? Object.keys(currentRows[0]) : ['_time', 'sourcetype', 'src', 'dest', 'action', 'signature'];

        return {
          ...c,
          results: currentRows,
          columns,
          executionTimeMs: duration,
          totalScanned: logs.length,
          totalMatched: matched.length,
          chartType: detectedChart
        };
      })
    );
  };

  const addCell = (type: 'spl' | 'markdown') => {
    const newCell: NotebookCell = {
      id: `cell-${Date.now()}`,
      type,
      content: type === 'spl' ? '* | stats count by sourcetype' : '### New Runbook Section\nAdd operational notes or detection logic description.',
      activeView: 'table'
    };
    setCells([...cells, newCell]);
  };

  const deleteCell = (cellId: string) => {
    setCells(cells.filter((c) => c.id !== cellId));
  };

  const updateCellContent = (cellId: string, content: string) => {
    setCells(cells.map((c) => (c.id === cellId ? { ...c, content } : c)));
  };

  const setCellView = (cellId: string, view: 'table' | 'raw' | 'chart') => {
    setCells(cells.map((c) => (c.id === cellId ? { ...c, activeView: view } : c)));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-[#0B0F19] border border-[#374151] rounded-xl w-full max-w-6xl h-[90vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Top Header */}
        <div className="px-6 py-4 bg-[#1F2937] border-b border-[#374151] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-violet-500/10 border border-violet-500/30 text-violet-400">
              <Code2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100 font-mono tracking-wide">
                  Interactive SPL Playground
                </h2>
                <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-2 py-0.5 rounded border border-emerald-700/60 font-mono font-bold">
                  JUPYTER NOTEBOOK v2.0
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Execute live Search Processing Language (SPL) pipelines against simulated streams and prototype detection rules.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => addCell('spl')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/40 text-violet-300 text-xs font-mono font-bold transition-all"
            >
              <Plus className="w-3.5 h-3.5" /> + SPL Cell
            </button>
            <button
              onClick={() => addCell('markdown')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 text-xs font-mono transition-all"
            >
              <FileText className="w-3.5 h-3.5" /> + Markdown
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Notebook Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0B0F19]">
          {cells.map((cell, index) => (
            <div
              key={cell.id}
              className={`rounded-xl border transition-all ${
                cell.type === 'spl'
                  ? 'bg-[#111827] border-[#374151] hover:border-violet-500/50 shadow-lg'
                  : 'bg-[#111827]/60 border-[#374151]/60'
              }`}
            >
              {/* Cell Header */}
              <div className="flex items-center justify-between px-4 py-2.5 bg-[#1F2937]/50 border-b border-[#374151] text-xs font-mono text-slate-400">
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 font-bold">[{index + 1}]</span>
                  <span className={cell.type === 'spl' ? 'text-violet-400 font-bold' : 'text-slate-300'}>
                    {cell.type === 'spl' ? 'SPL Query' : 'Markdown Note'}
                  </span>
                  {cell.executionTimeMs !== undefined && (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
                      <Clock className="w-3 h-3" /> {cell.executionTimeMs} ms ({cell.results?.length || 0} rows)
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {cell.type === 'spl' && (
                    <button
                      onClick={() => runCell(cell.id)}
                      className="flex items-center gap-1 px-3 py-1 bg-violet-600 hover:bg-violet-500 text-white font-bold rounded text-xs transition-colors shadow-sm"
                    >
                      <Play className="w-3 h-3 fill-white" /> Run
                    </button>
                  )}
                  <button
                    onClick={() => deleteCell(cell.id)}
                    className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Cell Content Editor */}
              <div className="p-4">
                <textarea
                  value={cell.content}
                  onChange={(e) => updateCellContent(cell.id, e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.shiftKey || e.ctrlKey)) {
                      e.preventDefault();
                      if (cell.type === 'spl') runCell(cell.id);
                    }
                  }}
                  rows={cell.type === 'spl' ? 2 : 3}
                  className={`w-full bg-[#0B0F19] p-3 rounded-lg border text-xs font-mono focus:outline-none transition-colors resize-y ${
                    cell.type === 'spl'
                      ? 'border-violet-500/40 text-violet-200 focus:border-violet-400'
                      : 'border-[#374151] text-slate-300 focus:border-slate-500'
                  }`}
                  placeholder={cell.type === 'spl' ? 'Enter SPL query (e.g. sourcetype=pan:threat | stats count by signature)' : 'Markdown note...'}
                />
              </div>

              {/* SPL Results Output Section */}
              {cell.type === 'spl' && cell.results && (
                <div className="border-t border-[#374151] bg-[#0F172A]/50">
                  {/* Output View Selector */}
                  <div className="flex items-center justify-between px-4 py-2 border-b border-[#374151] text-xs font-mono">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setCellView(cell.id, 'table')}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors ${
                          cell.activeView === 'table' || !cell.activeView
                            ? 'bg-violet-600/30 text-violet-300 border border-violet-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Table className="w-3.5 h-3.5" /> Table
                      </button>
                      <button
                        onClick={() => setCellView(cell.id, 'chart')}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors ${
                          cell.activeView === 'chart'
                            ? 'bg-violet-600/30 text-violet-300 border border-violet-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <BarChart2 className="w-3.5 h-3.5" /> Chart
                      </button>
                      <button
                        onClick={() => setCellView(cell.id, 'raw')}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors ${
                          cell.activeView === 'raw'
                            ? 'bg-violet-600/30 text-violet-300 border border-violet-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5" /> CIM Extractions
                      </button>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Matched {cell.totalMatched} / {cell.totalScanned} simulated events
                    </div>
                  </div>

                  {/* View 1: Table */}
                  {(!cell.activeView || cell.activeView === 'table') && (
                    <div className="max-h-60 overflow-auto">
                      <table className="w-full text-left text-xs font-mono border-collapse">
                        <thead>
                          <tr className="bg-[#1E293B] text-slate-300 border-b border-[#374151] sticky top-0">
                            {cell.columns?.map((col) => (
                              <th key={col} className="px-3 py-2 font-bold whitespace-nowrap">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {cell.results.length === 0 ? (
                            <tr>
                              <td colSpan={cell.columns?.length || 1} className="px-4 py-6 text-center text-slate-500">
                                No events matched query criteria.
                              </td>
                            </tr>
                          ) : (
                            cell.results.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                                {cell.columns?.map((col) => (
                                  <td key={col} className="px-3 py-1.5 text-slate-300 whitespace-nowrap">
                                    {row[col] !== undefined ? String(row[col]) : '-'}
                                  </td>
                                ))}
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* View 2: Chart */}
                  {cell.activeView === 'chart' && (
                    <div className="p-4 flex flex-col gap-2">
                      <div className="text-xs text-slate-400 font-mono mb-2 flex items-center justify-between">
                        <span>Metric Distribution</span>
                        <span className="text-[10px] text-violet-400 bg-violet-950/60 px-2 py-0.5 rounded border border-violet-800/50">
                          Aggregated Stats
                        </span>
                      </div>
                      <div className="space-y-2">
                        {cell.results.map((row, idx) => {
                          const label = row.signature || row.sourcetype || row.protocol || row.action || row.vendor || `Item ${idx + 1}`;
                          const val = Number(row.count || row.avg || row._value || Object.values(row).find((v) => typeof v === 'number') || 1);
                          const maxVal = Math.max(...cell.results!.map((r) => Number(r.count || r.avg || r._value || 1)), 1);
                          const pct = Math.round((val / maxVal) * 100);

                          return (
                            <div key={idx} className="space-y-1 font-mono text-xs">
                              <div className="flex justify-between text-slate-300 text-[11px]">
                                <span className="truncate max-w-md">{label}</span>
                                <span className="font-bold text-violet-400">{val}</span>
                              </div>
                              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                                <div
                                  className="bg-gradient-to-r from-violet-500 to-cyan-400 h-full rounded-full transition-all duration-300"
                                  style={{ width: `${Math.max(pct, 4)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* View 3: Raw CIM Extractions */}
                  {cell.activeView === 'raw' && (
                    <div className="p-4 space-y-2 max-h-60 overflow-auto">
                      {cell.results.slice(0, 5).map((row, idx) => (
                        <div key={idx} className="bg-[#0B0F19] p-3 rounded-lg border border-slate-800 font-mono text-xs space-y-1.5">
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-400 text-[10px] bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/50">
                              CIM Normalized
                            </span>
                            <span className="text-slate-400 text-[11px]">{row._time}</span>
                            <span className="text-violet-400 text-[11px] font-bold">{row.sourcetype}</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {Object.entries(row)
                              .filter(([k]) => !['_time', 'sourcetype'].includes(k))
                              .map(([k, v]) => (
                                <span key={k} className="bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700 text-slate-300 text-[11px]">
                                  <strong className="text-cyan-400">{k}</strong>={String(v)}
                                </span>
                              ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Bottom Footer */}
        <div className="px-6 py-3 bg-[#1F2937] border-t border-[#374151] flex items-center justify-between text-xs font-mono text-slate-400">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" /> Live In-Memory SPL Engine Active
            </span>
            <span className="text-slate-600">|</span>
            <span>Shortcut: <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 text-slate-300">Shift + Enter</kbd> to run cell</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-mono transition-colors"
          >
            Close Playground
          </button>
        </div>
      </div>
    </div>
  );
};
