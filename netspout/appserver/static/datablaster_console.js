/*
 * Splunk App: TA-network-data-blaster
 * View Script: datablaster_console.js
 * Clean enterprise network engineering interface
 */

require([
  'jquery',
  'splunkjs/mvc',
  'splunkjs/mvc/simplexml/ready!'
], function($, mvc) {
  'use strict';
  // Native server-owned run history. Text nodes prevent event/config HTML rendering.
  function mountNativeRunMonitor() {
    if (document.getElementById('native-run-monitor')) return;
    var anchor = document.getElementById('console-log-output') || document.getElementById('wizard-verification-container');
    if (!anchor || !anchor.parentNode) return;
    var panel = document.createElement('section');
    panel.id = 'native-run-monitor';
    panel.style.cssText = 'padding:12px;margin:12px 0;border:1px solid #64748b;white-space:pre-wrap;';
    var title = document.createElement('h3'); title.textContent = 'Native runs — collector acceptance is not indexing';
    var select = document.createElement('select'); select.setAttribute('aria-label', 'Select native run');
    var refresh = document.createElement('button'); refresh.textContent = 'Refresh runs';
    var verify = document.createElement('button'); verify.textContent = 'Verify in Splunk';
    var output = document.createElement('pre'); output.setAttribute('aria-live', 'polite');
    [title, select, refresh, verify, output].forEach(function(el) { panel.appendChild(el); });
    anchor.parentNode.insertBefore(panel, anchor);
    var runs = [];
    function render(run) {
      verify.disabled = !run || run.correlation !== 'SUPPORTED' || run.classification !== 'LOG' || !run.indexes.length;
      if (!run) { output.textContent = 'No retained native runs. Delivery metrics are not measured.'; return; }
      var lines = ['Run: ' + run.run_id, 'Execution: ' + run.execution_state,
        'Correlation: ' + run.correlation, 'Telemetry: ' + run.classification,
        'Indexes: ' + (run.indexes.join(', ') || 'not measured')];
      ['generated','attempted','accepted','failed','unknown'].forEach(function(k) {
        var v = run.counters[k]; lines.push(k + ': ' + (v === null || v === undefined ? 'not measured' : v));
      });
      lines.push('Splunk indexing: ' + run.verification.state + ' — ' + run.verification.message);
      if (verify.disabled) lines.push('Search verification is unsupported for this correlation path or scope.');
      output.textContent = lines.join('\n');
    }
    function request(payload) {
      return fetch(getRestUrl(), {method:'POST', headers:getHeaders(), body:JSON.stringify(payload)})
        .then(function(r) { if (!r.ok) throw new Error('unavailable'); return r.json(); })
        .then(function(data) { if (data.status !== 'success') throw new Error('unavailable'); return data; });
    }
    function reload() {
      var selected = select.value;
      refresh.disabled = true;
      return request({action:'native_runs'}).then(function(data) {
        runs = data.runs.slice().sort(function(a,b) { return b.started_at - a.started_at; });
        select.textContent = '';
        runs.forEach(function(run) { var option = document.createElement('option'); option.value = run.run_id;
          option.textContent = new Date(run.started_at * 1000).toISOString() + ' ' + run.execution.action + ' ' + run.run_id;
          select.appendChild(option); });
        if (runs.some(function(r) { return r.run_id === selected; })) select.value = selected;
        render(runs.find(function(r) { return r.run_id === select.value; }));
      }).catch(function() { output.textContent = 'Run history unavailable. No delivery or indexing conclusion can be drawn.'; verify.disabled = true; })
        .finally(function() { refresh.disabled = false; });
    }
    select.onchange = function() { render(runs.find(function(r) { return r.run_id === select.value; })); };
    refresh.onclick = reload;
    window.addEventListener('netspout-native-run', reload);
    verify.onclick = function() {
      verify.disabled = true;
      request({action:'verify_native_run',run_id:select.value}).then(function(data) {
        var index = runs.findIndex(function(r) { return r.run_id === data.run.run_id; });
        if (index >= 0) runs[index] = data.run;
        render(data.run);
      }).catch(function() { output.textContent = 'Verification ERROR: service unavailable; indexing is not verified.';
        renderErrorRetry(); });
    };
    function renderErrorRetry() { verify.disabled = false; }
    reload();
  }
  // Native SimpleXML views may finish mounting after this script loads.
  var nativeMonitorMountAttempts = 0;
  function mountNativeMonitorWhenReady() {
    mountNativeRunMonitor();
    if (!document.getElementById('native-run-monitor') && ++nativeMonitorMountAttempts < 30)
      setTimeout(mountNativeMonitorWhenReady, 100);
  }
  mountNativeMonitorWhenReady();


  function getRestUrl(queryStr) {
    var base = '';
    if (window.Splunk && window.Splunk.util && typeof window.Splunk.util.make_url === 'function') {
      base = window.Splunk.util.make_url('/splunkd/__raw/services/datablaster/execute');
    } else {
      var parts = window.location.pathname.split('/');
      var locale = (parts.length > 1 && parts[1]) ? parts[1] : 'en-US';
      base = '/' + locale + '/splunkd/__raw/services/datablaster/execute';
    }
    if (queryStr) {
      base += (base.indexOf('?') === -1 ? '?' : '&') + queryStr;
    }
    return base;
  }

  function getCsrfToken() {
    if (window.Splunk && window.Splunk.util && typeof window.Splunk.util.getConfigValue === 'function') {
      var fk = window.Splunk.util.getConfigValue('FORM_KEY');
      if (fk) return fk;
    }
    var match = document.cookie.match(/(?:^|;\s*)(?:splunkweb_csrf_token_[0-9]+|splunkweb_csrf_token)=([^;]*)/);
    return (match && match[1]) ? decodeURIComponent(match[1]) : '';
  }

  function getHeaders() {
    var h = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
    var csrf = getCsrfToken();
    if (csrf) {
      h['X-Splunk-Form-Key'] = csrf;
    }
    return h;
  }

  function log(msg) {
    var out = document.getElementById('console-log-output');
    if (!out) return;
    var ts = new Date().toLocaleTimeString();
    out.innerHTML = '<div style="margin-bottom: 2px;">[' + ts + '] ' + msg + '</div>' + out.innerHTML;
  }

  window.datablasterStopAll = function() {
    log('<span style="color: #ef4444; font-weight: bold;">STOPPING SIMULATION:</span> Terminating active background ingestion processes...');
    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ action: 'stop' })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.native_run) window.dispatchEvent(new Event('netspout-native-run'));
      log('<span style="color: #f59e0b; font-weight: bold;">STOPPED:</span> ' + (data.message || 'Simulation terminated.'));
    })
    .catch(function(err) {
      log('<span style="color: #ef4444;">ERROR:</span> ' + err.message);
    });
  };

  window.datablasterLaunchScenario = function(filename, name) {
    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "";
    var eps = cfg.target_eps || 1000;

    log('<span style="color: #0284c7; font-weight: bold;">LAUNCHING SCENARIO:</span> ' + name + ' (' + filename + ') at ' + eps + ' EPS...');

    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        action: 'start',
        scenario: filename,
        eps: eps,


      })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.native_run) window.dispatchEvent(new Event('netspout-native-run'));
      if (data.status === 'success' || data.code === 200 || data.pid) {
        log('<span style="color: #22c55e; font-weight: bold;">EXECUTION LAUNCHED:</span> Process PID ' + (data.pid || 'active') + ' launched; collector acceptance and indexing are not measured here.');
      } else {
        log('<span style="color: #ef4444;">RESPONSE:</span> ' + (data.message || JSON.stringify(data)));
      }
    })
    .catch(function(err) {
      log('<span style="color: #ef4444;">ERROR:</span> ' + err.message);
    });
  };

  function initConsole() {
    // Bind Scenario Launch Buttons via delegation
    $('.btn-launch-scenario').off('click').on('click', function() {
      var file = $(this).data('scenario');
      var name = $(this).data('name');
      window.datablasterLaunchScenario(file, name);
    });

    $('#btn-stop-all-console').off('click').on('click', window.datablasterStopAll);
    $('#btn-clear-console').off('click').on('click', function() {
      var out = document.getElementById('console-log-output');
      if (out) out.innerHTML = '';
    });

    // Check config
    fetch(getRestUrl('action=get_config'), { headers: getHeaders() })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.native_run) window.dispatchEvent(new Event('netspout-native-run'));
      if (data && data.config) {
        var c = data.config;
        log('Runtime initialized. Target HEC: ' + c.hec_url + ' | Default Rate: ' + c.target_eps + ' EPS');
      }
    })
    .catch(function() {});
  }

  var initAttempts = 0;
  function pollReady() {
    initAttempts++;
    if (document.getElementById('console-log-output')) {
      initConsole();
    } else if (initAttempts < 30) {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});

  $(document).on('click', '#btn-switch-to-wizard', function(e) {
    e.preventDefault();
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    window.location.href = '/' + locale + '/app/netspout/guided_onboarding';
  });

  $(document).on('click', '#btn-switch-to-console', function(e) {
    e.preventDefault();
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    window.location.href = '/' + locale + '/app/netspout/datablaster_console';
  });
