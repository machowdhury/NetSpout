import React from 'react';
import { Database, ShieldCheck, X } from 'lucide-react';

interface VendorAddonsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Compatibility entry point retained for the legacy canvas toolbar.
 *
 * The previous modal carried an independent hard-coded integration directory
 * with unsupported verification and CIM claims. Phase 2 routes this entry
 * point to the authoritative backend-driven catalog instead.
 */
export const VendorAddonsModal: React.FC<VendorAddonsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const openCatalog = () => {
    window.location.hash = '/catalog/splunk-integrations';
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-4">
      <section
        aria-labelledby="legacy-integrations-title"
        className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <header className="flex items-center justify-between border-b border-slate-700 px-5 py-4">
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-cyan-400" />
            <div>
              <h2 id="legacy-integrations-title" className="font-semibold text-slate-100">
                Splunk Integrations
              </h2>
              <p className="text-xs text-slate-400">Authoritative catalog required</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close integrations dialog"
            className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-4 p-5 text-sm text-slate-300">
          <div className="flex gap-3 rounded-lg border border-cyan-900 bg-cyan-950/40 p-4">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-cyan-400" />
            <p>
              The legacy hard-coded add-on directory has been retired because its
              sourcetype, CIM, and support claims did not carry per-record evidence.
              Use the catalog workspace for backend-validated integrations and explicit
              research, deprecated, lab-only, and unsupported states.
            </p>
          </div>
          <p className="text-xs text-slate-400">
            Existing telemetry behavior is unchanged. This replaces only the unverified
            presentation layer.
          </p>
          <div className="flex justify-end gap-2">
            <button type="button" className="button button--quiet" onClick={onClose}>
              Close
            </button>
            <button type="button" className="button button--primary" onClick={openCatalog}>
              Open authoritative catalog
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
