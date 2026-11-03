# Phase 1 UI simplification plan (plan only, nothing implemented)

Basis: file-level inspection of `main` (3f2e63f). I did not run or screenshot the UI for this plan.

Target: **Generate Data | Scenarios | Connections**, primary flow **Vendor → Product → Sourcetype → Preview → Generate → Verify**.

## What exists today
| Need | Existing piece | State |
|---|---|---|
| Pick vendor/product/sourcetype | `explorer/UniversalSearch.tsx` (free-text search), `catalog/*` views, `generator/GeneratorModesView.tsx` (modes A–D forms) | three different pickers, none is a Vendor → Product → Sourcetype drill-down |
| Preview | `GeneratorModesView` shows `sample_preview` from `/api/generate/sourcetype` (dispatch=false) | this endpoint and the monitored run use different code paths (`generate_sourcetype_batch` vs `prepare_sourcetype_entries`); both now go through `_NATIVE` for ASA and MDT metric, but not for other sourcetypes |
| Generate + delivery accounting | `explorer/SourcetypeStream.tsx` → monitored run (`main.py:2409`) → `monitor/LiveDeliveryMonitor.tsx` | the only path with per-event accounting |
| Verify | Live Delivery Monitor "indexed" tile (search by run id) | exists |
| Connections | `setup/SetupWizard.tsx` (Connection Center) | exists; requires search credentials as well as the HEC token |

## Smallest change set
1. **One page, "Generate Data"**: three dependent selects (vendor → product → sourcetype) fed by the existing catalog API, a **Preview** button (calls the same function as Generate with `dispatch=false`), a count field, **Generate** (monitored run), and the existing `LiveDeliveryMonitor` below as **Verify**. Reuse: `SourcetypeStream` run launch, `LiveDeliveryMonitor`. New: only the three selects.
2. **Hide** `GeneratorModesView` modes A/B/D forms (single event, data-source, incident pack) behind an "Advanced" toggle; keep mode C logic inside the new page.
3. **Show only grounded sourcetypes** in the picker. Today a sourcetype is selectable even when its sample replay is broken (see findings); the picker should list a sourcetype as "ready" only if it has a native generator or has passed a format contract, and label the rest "catalog only".
4. **Scenarios** and **Connections**: keep `Scenarios` as is; keep `SetupWizard` as **Connections** (separate task: allow HEC-only destinations).
5. Retire `UniversalSearch` as a primary page; keep as the search box above the vendor select.

## Wireframe
```
Generate Data | Scenarios | Connections
-------------------------------------------------------------
Vendor [Cisco v]  Product [ASA Firewall v]  Sourcetype [cisco:asa v]  (ready: native, TA 1620)
Count [50]   Index [idx_security_fw]            [Preview] [Generate]
-------------------------------------------------------------
Preview (first 3 events, same generator as Generate)
  Nov  3 10:00:00 asa-fw-01 %ASA-6-302013: Built outbound TCP ...
-------------------------------------------------------------
Verify   Generated 50 | HEC accepted 50 | Indexed (search by run id) 50   [Open in Splunk]
```

## Order of work (each step independently testable)
1. Sourcetype readiness flag from the contract tests (data, no UI).
2. The three selects + Preview calling the shared builder.
3. Wire Generate to the monitored run; reuse the monitor.
4. Hide advanced forms.
