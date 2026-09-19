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
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";
    var eps = cfg.target_eps || 1000;

    log('<span style="color: #0284c7; font-weight: bold;">LAUNCHING SCENARIO:</span> ' + name + ' (' + filename + ') at ' + eps + ' EPS...');

    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        action: 'start',
        scenario: filename,
        eps: eps,
        hec: hecUrl,
        token: token
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status === 'success' || data.code === 200 || data.pid) {
        log('<span style="color: #22c55e; font-weight: bold;">INGESTION ACTIVE:</span> Process PID ' + (data.pid || 'active') + ' streaming telemetry to Splunk HEC.');
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
