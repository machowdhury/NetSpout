import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Copy, Trash2, Search } from 'lucide-react';
import type { LogEntry } from '../types/topology';

interface LogTerminalProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  isRunning: boolean;
  onTogglePlay: () => void;
}

export const LogTerminal: React.FC<LogTerminalProps> = ({
  logs,
  onClearLogs
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [filterText, setFilterText] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((l) => {
    if (!filterText) return true;
    const q = filterText.toLowerCase();
    return (
      l.raw_log.toLowerCase().includes(q) ||
      l.device_id.toLowerCase().includes(q) ||
      l.action.toLowerCase().includes(q) ||
      l.src_ip.includes(q) ||
      l.dest_ip.includes(q)
    );
  });

  const handleCopy = () => {
    const text = filteredLogs.map((l) => l.raw_log).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderHighlightedLog = (entry: LogEntry) => {
    const isBreached = entry.status === 'breached' || entry.action === 'alerted';
    const isBlocked = entry.action === 'blocked' || entry.action === 'dropped';
    const isDegraded = entry.status === 'degraded';

    return (
      <div
        key={`${entry.timestamp}-${Math.random()}`}
        className={`py-1.5 px-2.5 font-mono text-[11px] leading-relaxed border-b border-slate-900/60 hover:bg-slate-900/80 transition-colors flex items-start gap-2.5 ${
          isBreached
            ? 'bg-rose-950/20 text-rose-200 border-l-2 border-l-rose-500'
            : isBlocked
            ? 'bg-amber-950/20 text-slate-300 border-l-2 border-l-amber-500'
            : isDegraded
            ? 'bg-sky-950/20 text-sky-200 border-l-2 border-l-sky-400'
            : 'text-slate-300 border-l-2 border-l-cyan-500/40'
        }`}
      >
        <span
          className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded font-mono uppercase ${
            entry.action === 'blocked' || entry.action === 'dropped'
              ? 'bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/50'
              : entry.action === 'alerted'
              ? 'bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/50 animate-pulse'
              : 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/50'
          }`}
        >
          {entry.action}
        </span>

        <div className="flex-1 break-all">
          <span className="text-cyan-400 font-semibold">{entry.timestamp} </span>
          <span className="text-purple-300 font-semibold">[{entry.device_id}] </span>
          {entry.sourcetype && (
            <span className="text-[9px] bg-slate-900 text-cyan-300 border border-cyan-800/80 px-1 py-0.2 rounded font-mono mr-1.5">
              {entry.sourcetype}
            </span>
          )}
          <span className="text-slate-400">src=</span>
          <span className="text-yellow-400">{entry.src_ip} </span>
          <span className="text-slate-400">dst=</span>
          <span className="text-emerald-400">{entry.dest_ip} </span>
          <span className="text-slate-400">proto=</span>
          <span className="text-sky-300">{entry.protocol} </span>
          <span className="text-slate-400">dur=</span>
          <span className="text-slate-300">{entry.duration} </span>
          <span className="text-slate-400">sig=&quot;</span>
          <span
            className={
              isBreached
                ? 'text-rose-400 font-bold'
                : isBlocked
                ? 'text-amber-400 font-medium'
                : isDegraded
                ? 'text-sky-400 font-medium'
                : 'text-indigo-300'
            }
          >
            {entry.signature}
          </span>
          <span className="text-slate-400">&quot; </span>
          <span className="text-slate-400">status=</span>
          <span
            className={`font-bold ${
              isBreached
                ? 'text-rose-400 underline animate-pulse'
                : isBlocked
                ? 'text-amber-400'
                : isDegraded
                ? 'text-sky-400'
                : 'text-emerald-400'
            }`}
          >
            {entry.status}
          </span>
        </div>
      </div>
    );
  };

  return (
    <aside className="w-[450px] bg-[#1F2937] border-l border-[#374151] flex flex-col h-full overflow-hidden shrink-0 select-none z-20">
      {/* Terminal Header */}
      <div className="p-3 border-b border-[#374151] bg-[#1F2937] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 font-mono">
            Splunk Log Terminal
          </h2>
          <span className="text-[10px] bg-slate-900 border border-slate-800 text-cyan-400 px-1.5 py-0.2 rounded font-mono">
            KV STREAM
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-0.8 text-[10px] font-mono rounded border transition-colors cursor-pointer ${
              autoScroll
                ? 'bg-cyan-950 border-cyan-800 text-cyan-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
            title="Toggle Auto-Scroll"
          >
            AutoScroll: {autoScroll ? 'ON' : 'OFF'}
          </button>

          <button
            onClick={handleCopy}
            className="p-1 text-slate-400 hover:text-cyan-400 hover:bg-slate-900 rounded transition-colors cursor-pointer"
            title="Copy Logs to Clipboard"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClearLogs}
            className="p-1 text-slate-400 hover:text-red-400 hover:bg-slate-900 rounded transition-colors cursor-pointer"
            title="Clear Terminal Output"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-2 border-b border-slate-800/60 bg-slate-900/50 flex items-center gap-2">
        <Search className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <input
          type="text"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Filter logs (IP, action, signature, device)..."
          className="w-full bg-transparent text-xs text-slate-200 placeholder-slate-600 focus:outline-none font-mono"
        />
        {filterText && (
          <button
            onClick={() => setFilterText('')}
            className="text-[10px] text-slate-500 hover:text-slate-300 font-mono cursor-pointer"
          >
            Clear
          </button>
        )}
      </div>

      {/* Log Stream Container */}
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto bg-[#070b14] p-1 select-text scrollbar-thin scrollbar-thumb-slate-800"
      >
        {filteredLogs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-600 font-mono text-xs">
            <Terminal className="w-8 h-8 mb-2 stroke-[1.5] text-slate-700" />
            <p>Log Terminal Standing By</p>
            <p className="text-[10px] text-slate-600 mt-1">
              Click &apos;START SIMULATION&apos; in Top Bar to stream path-evaluated Splunk KV logs
            </p>
          </div>
        ) : (
          filteredLogs.map((entry) => renderHighlightedLog(entry))
        )}
      </div>

      {/* Terminal Footer Metrics */}
      <div className="p-2 bg-slate-950 border-t border-slate-800/80 text-[10px] font-mono text-slate-500 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span>Buffer: <b className="text-slate-300">{logs.length}</b></span>
          <span>Filtered: <b className="text-cyan-400">{filteredLogs.length}</b></span>
        </div>
        <div className="flex items-center gap-2">
          {copied && <span className="text-emerald-400">Copied to clipboard!</span>}
          <span className="text-slate-600">Rate: 2 logs/sec</span>
        </div>
      </div>
    </aside>
  );
};
