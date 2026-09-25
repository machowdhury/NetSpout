import React, { useState, useMemo } from 'react';
import { 
  Search, Shield, Activity, Wifi, Server, Globe, Radio, 
  CheckCircle2, ChevronRight, ChevronDown, Clock, Filter, AlertCircle
} from 'lucide-react';
import type { UseCase } from '../../types/workflow';

interface StepChooseProps {
  useCases: UseCase[];
  selectedUseCase: UseCase | null;
  onSelectUseCase: (uc: UseCase) => void;
  onNext: () => void;
  loading: boolean;
  error: string | null;
}

const CATEGORIES = [
  { id: 'ALL', label: 'All Use Cases', icon: Activity },
  { id: 'NETWORK_OPERATIONS', label: 'Network Operations', icon: Activity },
  { id: 'WAN', label: 'WAN & SD-WAN', icon: Globe },
  { id: 'CAMPUS', label: 'Campus & LAN', icon: Server },
  { id: 'WIRELESS', label: 'Wireless', icon: Wifi },
  { id: 'DATACENTER', label: 'Data Center', icon: Server },
  { id: 'SECURITY', label: 'Security & Zero Trust', icon: Shield },
  { id: 'SERVICE_PROVIDER', label: 'Service Provider', icon: Radio },
  { id: 'SERVICE_ASSURANCE', label: 'Service Assurance', icon: Activity },
];

export const StepChoose: React.FC<StepChooseProps> = ({
  useCases,
  selectedUseCase,
  onSelectUseCase,
  onNext,
  loading,
  error
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedDetailsId, setExpandedDetailsId] = useState<string | null>(null);

  const filteredUseCases = useMemo(() => {
    return useCases.filter((uc) => {
      const matchesCat = 
        selectedCategory === 'ALL' || 
        uc.category.toUpperCase() === selectedCategory ||
        (selectedCategory === 'CAMPUS' && uc.category.toUpperCase() === 'CAMPUS_LAN');

      const q = searchQuery.toLowerCase().trim();
      const matchesQuery = !q || (
        uc.name.toLowerCase().includes(q) ||
        uc.description.toLowerCase().includes(q) ||
        uc.objective.toLowerCase().includes(q) ||
        uc.vendors.some(v => v.toLowerCase().includes(q)) ||
        uc.sourcetypes.some(s => s.toLowerCase().includes(q))
      );

      return matchesCat && matchesQuery;
    });
  }, [useCases, selectedCategory, searchQuery]);

  const toggleDetails = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setExpandedDetailsId(prev => prev === id ? null : id);
  };

  const getDifficultyColor = (diff: string) => {
    switch (diff.toUpperCase()) {
      case 'BEGINNER': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'ADVANCED': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'INTERMEDIATE':
      default: return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>1. Choose Use Case</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              {filteredUseCases.length} Available
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            What do you want to prove? Select an operational failure scenario or security detection use case to demonstrate.
          </p>
        </div>

        {selectedUseCase && (
          <button
            onClick={onNext}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition shadow-lg shadow-cyan-900/30 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            aria-label="Proceed to Preview"
          >
            <span>Preview Selection</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Category Filter Pills & Search */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const active = selectedCategory === cat.id;
            const btnClass = active 
              ? "bg-cyan-600 text-white border-cyan-500 shadow-sm" 
              : "bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200";
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={"flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition border " + btnClass}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        <div className="relative w-full">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search by keyword, vendor (Cisco, Palo Alto, Arista...), sourcetype, or failure mode..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition"
          />
        </div>
      </div>

      {/* Error / Loading / Empty States */}
      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading canonical use-case catalog...</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-sm">Error loading use cases</h4>
            <p className="text-xs text-rose-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && filteredUseCases.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2 p-8 border border-dashed border-slate-800 rounded-xl">
          <Filter className="w-8 h-8 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">No matching use cases found</p>
          <p className="text-xs text-slate-500">Try clearing your search query or selecting another category.</p>
        </div>
      )}

      {/* Use Case Cards Grid */}
      {!loading && !error && filteredUseCases.length > 0 && (
        <div className="flex-1 overflow-y-auto pr-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
          {filteredUseCases.map((uc) => {
            const isSelected = selectedUseCase?.id === uc.id;
            const isExpanded = expandedDetailsId === uc.id;
            const cardClass = isSelected
              ? "bg-cyan-950/30 border-cyan-500 shadow-md shadow-cyan-950/40"
              : "bg-slate-900/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900";

            return (
              <div
                key={uc.id}
                onClick={() => onSelectUseCase(uc)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectUseCase(uc);
                  }
                }}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                className={"relative flex flex-col text-left p-4 rounded-xl border transition cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-cyan-500/80 " + cardClass}
              >
                {/* Card Top Row: Category & Badges */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider truncate">
                    {uc.domain}
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={"text-[10px] font-bold px-1.5 py-0.5 rounded border " + getDifficultyColor(uc.difficulty)}>
                      {uc.difficulty}
                    </span>
                    <span className="text-[10px] font-medium text-slate-400 flex items-center gap-1 bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700/50">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {uc.estimated_runtime_sec}s
                    </span>
                  </div>
                </div>

                {/* Card Title */}
                <h3 className="text-base font-semibold text-slate-100 group-hover:text-cyan-300 transition line-clamp-2 leading-snug mb-1">
                  {uc.name}
                </h3>

                {/* Description */}
                <p className="text-xs text-slate-400 line-clamp-2 mb-3 leading-relaxed">
                  {uc.description}
                </p>

                {/* Vendors Scope Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {uc.vendors.slice(0, 3).map((v, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/90 text-slate-300 border border-slate-700/60 font-mono">
                      {v.replace('_', ' ')}
                    </span>
                  ))}
                  {uc.vendors.length > 3 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                      +{uc.vendors.length - 3} more
                    </span>
                  )}
                </div>

                {/* Card Footer: Objective & Action */}
                <div className="mt-auto pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <button
                    onClick={(e) => toggleDetails(e, uc.id)}
                    className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px] font-medium transition focus:outline-none"
                  >
                    <span>{isExpanded ? 'Hide Details' : 'Advanced Details'}</span>
                    <ChevronDown className={"w-3 h-3 transition-transform " + (isExpanded ? "rotate-180" : "")} />
                  </button>

                  <div className="flex items-center gap-1">
                    {isSelected ? (
                      <span className="flex items-center gap-1 text-cyan-400 font-semibold text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Selected
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Click to Select</span>
                    )}
                  </div>
                </div>

                {/* Collapsible Advanced Details */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] space-y-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div>
                      <span className="text-slate-500 font-medium block">Objective:</span>
                      <p className="text-slate-300 mt-0.5">{uc.objective}</p>
                    </div>
                    <div>
                      <span className="text-slate-500 font-medium block">Target Sourcetypes:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {uc.sourcetypes.map((st, i) => (
                          <code key={i} className="bg-slate-900 text-cyan-300 px-1 py-0.5 rounded border border-slate-800 font-mono text-[10px]">
                            {st}
                          </code>
                        ))}
                      </div>
                    </div>
                    {uc.validation_rules.length > 0 && (
                      <div>
                        <span className="text-slate-500 font-medium block">Validation Rule:</span>
                        <p className="text-slate-300 text-[10px] mt-0.5 font-mono">
                          {uc.validation_rules[0].name} ({uc.validation_rules[0].type})
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
