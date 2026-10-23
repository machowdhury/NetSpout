/* NetSpout PulseForge: read-only discovery over generated canonical relationships. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; return; }
  require(['jquery', 'splunkjs/mvc', 'splunkjs/mvc/searchmanager', 'splunkjs/mvc/simplexml/ready!'],
    function ($, mvc, SearchManager) { api.mount(root, SearchManager); });
}(typeof window !== 'undefined' ? window : this, function () {
  'use strict';
  function values(row, field) { return Array.isArray(row[field]) ? row[field] : [row[field] || '']; }
  function filter(entries, query, facets) {
    var terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    return entries.filter(function (row) {
      var text = JSON.stringify(row).toLowerCase();
      return terms.every(function (term) { return text.indexOf(term) >= 0; }) &&
        Object.keys(facets).every(function (field) {
          return !facets[field].length || facets[field].some(function (value) { return values(row, field).indexOf(value) >= 0; });
        });
    });
  }
  function page(rows, number) { return rows.slice(number * 40, (number + 1) * 40); }
  function scope(index, run) {
    if (!/^[A-Za-z0-9_][A-Za-z0-9_-]{0,79}$/.test(index) ||
        !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(run)) { throw new Error('Invalid search scope'); }
    return 'search index="' + index + '" netspout_run_id="' + run + '"';
  }
  function assess(data, required) {
    if (!data || !data.rows || data.rows.length !== 1) { return 'INCONCLUSIVE'; }
    var map = {};
    data.fields.forEach(function (f, i) { map[typeof f === 'string' ? f : f.name] = data.rows[0][i]; });
    var count = Number(map.observed_records);
    if (!Number.isFinite(count) || count < 0) { return 'INCONCLUSIVE'; }
    if (!count) { return 'MISSING_DATA'; }
    return required.every(function (field) { return Number(map['present_' + field]) === count; }) ? 'FIELDS_PRESENT' : 'MISSING_FIELDS';
  }
  function mount(win, SearchManager) {
    var doc = win.document, host = doc.getElementById('pf-discovery');
    if (!host) { return; }
    function node(tag, text, parent) {
      var el = doc.createElement(tag); if (text !== undefined) { el.textContent = text; }
      if (parent) { parent.appendChild(el); } return el;
    }
    function url(path) {
      if (win.Splunk && win.Splunk.util) { return win.Splunk.util.make_url(path); }
      return '/' + (win.location.pathname.split('/')[1] || 'en-US') + path;
    }
    function link(text, view, parent) { var a = node('a', text, parent); a.href = url('/app/netspout/' + view); return a; }
    var status = doc.getElementById('pf-discovery-status'), list = doc.getElementById('pf-results'),
      detail = doc.getElementById('pf-detail'), input = doc.getElementById('pf-search'),
      facets = {}, entries = [], currentPage = 0, destinations = null, activeSearch = null, selectedScenario = null;
    function related(label, kind, ids) {
      if (!ids || !ids.length) { node('p', label + ': none established in this slice.', detail); return; }
      node('h4', label, detail);
      ids.forEach(function (id) {
        var row = entries.find(function (e) { return e.kind === kind && e.id === id; });
        if (row) { var b = node('button', row.title, detail); b.type = 'button'; b.onclick = function () { show(row); }; }
      });
    }
    function show(row) {
      if (activeSearch) { activeSearch.cancel(); activeSearch = null; }
      if (row.kind === 'scenario') { selectedScenario = row.incident_contract || null; }
      else if (row.kind !== 'dashboard') { selectedScenario = null; }
      detail.textContent = ''; node('h3', row.title, detail);
      node('p', row.kind + ' • ' + row.id + ' • ' + row.readiness, detail);
      node('p', row.description, detail);
      if (row.required_telemetry) { node('h4', 'Required telemetry (a requirement is not native compatibility)', detail); node('p', row.required_telemetry.join(', '), detail); }
      if (row.formats) { node('p', 'Format: ' + (row.formats.join(', ') || 'Unknown; review required'), detail); }
      if (row.vendors) { node('p', 'Vendor/product: ' + (row.vendors.join(', ') || 'Not established'), detail); }
      if (row.profiles) {
        node('h4', 'Versioned integration profiles', detail);
        if (!row.profiles.length) { node('p', 'Selected-version parser verification not established.', detail); }
        row.profiles.forEach(function (p) { node('p', p.profile_id + ' • ' + p.product + ' • candidate version ' + (p.app_version || 'unknown') + ' • ' + p.coverage + ' / ' + p.verification_state, detail); });
      }
      if (row.required_fields) { node('p', 'Required structured fields: ' + row.required_fields.join(', '), detail); }
      (row.prerequisites || []).forEach(function (p) { node('p', 'Prerequisite (not checked): ' + p, detail); });
      if (row.incident_contract) {
        node('p', 'Runtime scenario ID: ' + row.incident_contract.runtime_scenario_id, detail);
        node('p', 'Simulated KPI names: ' + row.incident_contract.metric_names.join(', '), detail);
      }
      Object.keys(row.field_provenance || {}).forEach(function (field) { node('p', field + ': ' + row.field_provenance[field], detail); });
      (row.gaps || []).forEach(function (gap) { node('p', 'Gap: ' + gap, detail); });
      (row.evidence || []).forEach(function (e) {
        if (/^https:\/\//.test(e.reference || '')) { var a = node('a', e.title || 'Evidence', detail); a.href = e.reference; a.target = '_blank'; a.rel = 'noopener noreferrer'; }
        else { node('p', 'Evidence reference: ' + (e.reference || e.title || 'unknown'), detail); }
      });
      if (row.kind !== 'sourcetype') { related('Sourcetypes', 'sourcetype', row.sourcetypes); }
      if (row.metric_sourcetypes) { related('Metric sourcetypes (KPI prerequisites)', 'sourcetype', row.metric_sourcetypes); }
      if (row.kind !== 'scenario') { related('Related scenarios', 'scenario', row.scenario_ids); }
      if (row.kind !== 'dashboard') {
        var ds = row.dashboard_ids || [];
        if (ds.length) { related('Primary recommended dashboard', 'dashboard', ds.slice(0, 1)); related('Related dashboards', 'dashboard', ds.slice(1)); }
        else { node('p', 'Recommended dashboard: not yet established for this contract.', detail); }
      }
      if (row.kind === 'scenario') {
        node('h4', 'Saved destinations', detail);
        if (destinations === null) { node('p', 'Unavailable or not authorized. Open Destination Manager to review settings.', detail); }
        else if (!destinations.length) { node('p', 'No saved destinations.', detail); }
        else { destinations.forEach(function (d) { node('p', d.name + ' • ' + d.protocol + ' • ' + (d.enabled ? 'enabled' : 'disabled') + ' • signals: ' + d.signals.join(', ') + '. Final compatibility is validated at run start.', detail); }); }
        link('Open Run Console (select this scenario and a named destination)', 'datablaster_console', detail);
        link('Open Destination Manager', 'configuration', detail);
      }
      if (row.kind === 'dashboard') {
        node('p', 'Required fields: ' + row.required_fields.join(', '), detail);
        var openDashboard = link('Open Splunk dashboard', row.view, detail);
        if (selectedScenario && row.scenario_ids.some(function (sid) { return sid === selectedScenario.runtime_scenario_id || sid === 'network_' + selectedScenario.runtime_scenario_id; })) {
          openDashboard.href += '?form.scenario_id=' + encodeURIComponent(selectedScenario.runtime_scenario_id);
        }
        node('p', 'KPI prerequisites: configured local metrics index, metric sourcetype (' + (row.metric_sourcetypes || []).join(', ') + ') and preserved run/scenario/device/phase dimensions. NOT_CHECKED; log readiness does not prove metric availability.', detail);
        var label = node('label', 'Local event index ', detail), idx = node('input', undefined, label); idx.value = 'idx_network_ops';
        label = node('label', 'Server-owned run UUID ', detail); var run = node('input', undefined, label);
        var state = node('p', 'NOT_CHECKED — local indexed data only; no delivery claim.', detail);
        var check = node('button', 'Check local data and fields (one bounded search)', detail); check.type = 'button';
        check.onclick = function () {
          var base;
          try { base = scope(idx.value, run.value); } catch (e) { state.textContent = 'Invalid index or run UUID; no search started.'; return; }
          check.disabled = true; state.textContent = 'CHECKING';
          var search, timer, finished = false;
          function finish(text) {
            if (finished) { return; } finished = true; win.clearTimeout(timer); check.disabled = false;
            state.textContent = text + ' — local observations only, not receiver or downstream delivery proof.';
            if (search) { search.cancel(); } activeSearch = null;
          }
          try {
            search = new SearchManager({id: 'pf_discovery_' + Date.now(), search: base + ' (' + row.sourcetypes.map(function (s) { return 'sourcetype="' + s + '"'; }).join(' OR ') + ') | stats count as observed_records ' + row.required_fields.map(function (f) { return 'count(' + f + ') as present_' + f; }).join(' '), earliest_time: '-24h', latest_time: 'now', autostart: false, cache: false});
            activeSearch = search;
            timer = win.setTimeout(function () { finish('ERROR: search timeout'); }, 10000);
            search.on('search:error', function () { finish('ERROR: search unavailable or not authorized'); });
            search.on('search:failed', function () { finish('ERROR: search failed'); });
            search.on('search:done', function (event) {
              if (!event.content || (event.content.isDone !== true && event.content.isDone !== '1' && event.content.isDone !== 1) || event.content.isFinalized || event.content.isFailed) { finish('INCONCLUSIVE: incomplete search'); return; }
              var results = search.data('results', {count: 1, output_mode: 'json_rows'});
              results.on('data', function () { finish(assess(results.data(), row.required_fields)); });
            });
            search.startSearch();
          } catch (e) { finish('ERROR: local search could not start'); }
        };
      }
    }
    function render() {
      var rows = filter(entries, input.value, facets); currentPage = Math.min(currentPage, Math.max(0, Math.ceil(rows.length / 40) - 1));
      status.textContent = rows.length + ' results • page ' + (currentPage + 1) + ' of ' + Math.max(1, Math.ceil(rows.length / 40));
      list.textContent = '';
      page(rows, currentPage).forEach(function (row) { var b = node('button', row.title + ' — ' + row.kind + ' — ' + row.readiness, list); b.type = 'button'; b.onclick = function () { show(row); }; });
      doc.getElementById('pf-prev').disabled = currentPage === 0;
      doc.getElementById('pf-next').disabled = (currentPage + 1) * 40 >= rows.length;
    }
    input.oninput = function () { currentPage = 0; render(); };
    doc.getElementById('pf-prev').onclick = function () { currentPage--; render(); };
    doc.getElementById('pf-next').onclick = function () { currentPage++; render(); };
    doc.getElementById('pf-clear').onclick = function () { input.value = ''; Object.keys(facets).forEach(function (key) { facets[key] = []; }); host.querySelectorAll('input[type=checkbox]').forEach(function (el) { el.checked = false; }); currentPage = 0; render(); };
    win.fetch(url('/static/app/netspout/discovery_catalog.json')).then(function (r) { if (!r.ok) { throw new Error(); } return r.json(); }).then(function (data) {
      entries = data.entries;
      input.value = new URLSearchParams(win.location.search || '').get('q') || input.value;
      [['domain', 'Browse domains'], ['industries', 'Industry'], ['vendors', 'Vendor / product'], ['readiness', 'Readiness'], ['kind', 'Record type']].forEach(function (pair) {
        var field = pair[0]; facets[field] = [];
        var box = node('details', undefined, doc.getElementById('pf-filters')); node('summary', pair[1], box); box.open = field === 'domain';
        Array.from(new Set(entries.flatMap(function (row) { return values(row, field); }))).filter(Boolean).sort().forEach(function (value) {
          var label = node('label', undefined, box), cb = node('input', undefined, label); cb.type = 'checkbox'; node('span', value, label);
          cb.onchange = function () { facets[field] = cb.checked ? facets[field].concat(value) : facets[field].filter(function (v) { return v !== value; }); currentPage = 0; render(); };
        });
      }); render();
    }).catch(function () { status.textContent = 'Discovery catalog unavailable; no results were inferred.'; });
    var headers = {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'};
    if (win.Splunk && win.Splunk.util) { headers['X-Splunk-Form-Key'] = win.Splunk.util.getConfigValue('FORM_KEY') || ''; }
    win.fetch(url('/splunkd/__raw/services/datablaster/execute'), {method: 'POST', headers: headers, body: JSON.stringify({action: 'list_destinations'})})
      .then(function (r) { if (!r.ok) { throw new Error(); } return r.json(); })
      .then(function (data) { destinations = data.destinations.map(function (d) { return {name: d.name, protocol: d.protocol, enabled: d.enabled, signals: d.signals}; }); })
      .catch(function () { destinations = null; });
  }
  return {filter: filter, page: page, scope: scope, assess: assess, mount: mount};
}));
