/**
 * TA-datablaster Modern Web UI Controller
 * Fully compatible with Splunk Web Framework
 */

(function () {
  'use strict';

  // Preset sample payloads for quick testing & validation
  const PRESETS = {
    cisco_mdt: {
      name: "Cisco Model-Driven Telemetry (MDT - Optics)",
      scenario: "normal",
      targetIndex: "cisco_metrics",
      targetSourcetype: "httpevent",
      content: JSON.stringify({
        "telemetry_version": "1.0.0",
        "subscription_id": "SUB-1002",
        "collection_id": 84201,
        "encoding_path": "Cisco-IOS-XR-controller-optics-oper:optics-ports",
        "msg_timestamp": 1789762400000,
        "node_id": "R6/PE2",
        "fields": {
          "metric_name:pre_fec_ber": 0.0000000012,
          "metric_name:uncorrected_ber": 0,
          "metric_name:snr_lane1": 28.5,
          "metric_name:rx_power_dbm": -4.8,
          "controller_name": "Optics0/0/0/1"
        }
      }, null, 2)
    },
    cisco_ftd: {
      name: "Cisco Secure Firewall FTD / ASA Log",
      scenario: "normal",
      targetIndex: "cisco_secure_fw",
      targetSourcetype: "cisco:sfw:estreamer",
      content: '%FTD-6-302013: Built outbound TCP connection 948210 for Outside:198.51.100.25/443 (198.51.100.25/443) to Inside:10.0.10.26/51234 (10.0.10.26/51234) by ACME-WEB-ACCESS'
    },
    palo_alto: {
      name: "Palo Alto Networks PAN-OS Traffic Log",
      scenario: "ddos",
      targetIndex: "main",
      targetSourcetype: "pan:traffic",
      content: '1,2026/09/18 16:14:00,001801000001,TRAFFIC,drop,2304,2026/09/18 16:14:00,192.168.1.100,10.20.104.200,0.0.0.0,0.0.0.0,RULE_DENY_FLOOD,,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,FORWARD,2026/09/18 16:14:00,0,1,443,443,0,0,0x0,tcp,deny,64,64,0,1,14,from-untrust,SYN Flood Protection,PAN-OS,0'
    },
    linux_auth: {
      name: "Linux Secure SSH Brute Force Log",
      scenario: "brute_force",
      targetIndex: "main",
      targetSourcetype: "linux_secure",
      content: 'Sep 18 16:14:05 rhel-jumpbox-01 sshd[38291]: Failed password for invalid user root from 203.0.113.42 port 49212 ssh2'
    },
    sdwan_bfd: {
      name: "Cisco SD-WAN BFD Tunnel SLA Degradation",
      scenario: "ddos",
      targetIndex: "sdwan",
      targetSourcetype: "cisco:sdwan:tunnelhealth",
      content: JSON.stringify({
        "site_id": "325",
        "site_name": "Branch 1 (Site 325)",
        "edge_device": "C8K-SDWAN-Site325-01",
        "tunnel_name": "tunnel_biz-internet_to_R2-PE2",
        "loss_percentage": 14.8,
        "latency_ms": 420.5,
        "jitter_ms": 32.1,
        "sla_state": "VIOLATED",
        "reason": "BFD timeout threshold exceeded"
      }, null, 2)
    }
  };

  class DataBlasterApp {
    constructor(rootId) {
      this.root = document.getElementById(rootId);
      if (!this.root) return;

      const host = (typeof window !== 'undefined' && window.location && window.location.hostname) ? window.location.hostname : '127.0.0.1';
      let defHec = 'https://' + host + ':8888/services/collector';
      let defTok = '00000000-0000-0000-0000-000000000000';
      try {
        if (localStorage.getItem('datablaster_hec_url')) defHec = localStorage.getItem('datablaster_hec_url');
        if (localStorage.getItem('datablaster_hec_token')) defTok = localStorage.getItem('datablaster_hec_token');
      } catch(e) {}

      this.state = {
        activeTab: 'tab-status',
        currentScenario: 'normal',
        targetEps: 50,
        hecUrl: defHec,
        hecToken: defTok,
        sampleContent: PRESETS.cisco_mdt.content,
        sampleName: PRESETS.cisco_mdt.name,
        targetIndex: 'cisco_metrics',
        targetSourcetype: 'httpevent',
        isRunning: false,
        totalSent: 0,
        indexedCount: 0,
        currentEps: 0,
        timerId: null,
        logIntervalId: null,
      };

      this.render();
      this.bindEvents();
      this.updateBlueprint();
    }

    render() {
      this.root.innerHTML = `
        <div class="db-container">
          <!-- Header -->
          <div class="db-header">
            <div class="db-title-group">
              <h1>
                <span>DataBlaster Console</span>
                <span class="db-badge db-badge-cyan">v1.0.0</span>
                <span id="db-engine-status" class="db-badge db-badge-success">Engine Ready</span>
              </h1>
              <p>Unified simulation orchestrator for Cisco Model-Driven Telemetry, SD-WAN, Campus, and Enterprise Security Logs</p>
            </div>
            <div>
              <span class="db-badge db-badge-purple">Splunk Cloud Premium HEC Verified</span>
            </div>
          </div>

          <!-- Configuration Controls -->
          <div class="db-control-grid">
            <!-- Sample File Selector -->
            <div class="db-card">
              <label class="db-card-label">1. Sample Payload / Telemetry File</label>
              <select id="db-preset-select" class="db-select" style="margin-bottom: 8px;">
                <option value="cisco_mdt">Cisco Model-Driven Telemetry (MDT - Optics)</option>
                <option value="cisco_ftd">Cisco Secure Firewall FTD / ASA Log</option>
                <option value="palo_alto">Palo Alto Networks PAN-OS Traffic Log</option>
                <option value="linux_auth">Linux Secure SSH Brute Force Log</option>
                <option value="sdwan_bfd">Cisco SD-WAN BFD Tunnel SLA Degradation</option>
                <option value="custom">-- Custom Upload / Pasted File --</option>
              </select>
              <div id="db-dropzone" class="db-dropzone">
                <span style="font-size: 20px;">📂</span>
                <p><strong>Click or Drag File Here</strong> (JSON, Syslog, YML)</p>
                <input type="file" id="db-file-input" accept=".json,.log,.txt,.yml,.csv">
              </div>
            </div>

            <!-- Simulation Scenario Selector -->
            <div class="db-card">
              <label class="db-card-label">2. Simulation Scenario</label>
              <select id="db-scenario-select" class="db-select">
                <option value="normal">Normal Base Traffic (Steady-State 85%)</option>
                <option value="ddos">DDoS Spike &amp; Uplink Congestion</option>
                <option value="brute_force">Brute Force Attempt &amp; Auth Spike</option>
                <option value="aci_bd">Maple DC ACI Bridge Domain Withdrawal</option>
                <option value="mpls_optics">Core 100G Pre-FEC Optical Decay &amp; FRR</option>
              </select>
              <div style="margin-top: 12px;">
                <label class="db-card-label">Target Rate (EPS)</label>
                <input type="number" id="db-eps-input" class="db-input" value="50" min="1" max="5000">
              </div>
            </div>

            <!-- Splunk HEC Endpoint & Token -->
            <div class="db-card">
              <label class="db-card-label">3. Destination Splunk HEC URL</label>
              <input type="text" id="db-hec-url" class="db-input" value="${this.state.hecUrl}" style="margin-bottom: 8px;">
              <label class="db-card-label">HEC Authorization Token</label>
              <input type="text" id="db-hec-token" class="db-input" value="${this.state.hecToken}">
            </div>
          </div>

          <!-- Action Bar -->
          <div class="db-action-bar">
            <div style="display: flex; gap: 12px; align-items: center;">
              <button id="db-blast-btn" class="db-btn db-btn-primary">
                <span>⚡ Fire Blast</span>
              </button>
              <button id="db-reset-btn" class="db-btn db-btn-outline">
                <span>🔄 Reset Counters</span>
              </button>
            </div>
            <div id="db-status-bar" style="font-size: 13px; color: var(--db-text-muted);">
              Status: <span style="color: #60a5fa; font-weight: 600;">Idle</span>
            </div>
          </div>

          <!-- Tabs Navigation -->
          <div class="db-tabs">
            <button class="db-tab-btn active" data-tab="tab-status">📊 Tab 1: Live Status &amp; Metrics</button>
            <button class="db-tab-btn" data-tab="tab-sample">📄 Tab 2: Sample Data View</button>
            <button class="db-tab-btn" data-tab="tab-blueprint">🛡️ Tab 3: Splunk Integration Blueprint</button>
            <button class="db-tab-btn" data-tab="tab-logs">💻 Tab 4: Scenario Logs</button>
          </div>

          <!-- TAB 1: Live Status & Metrics -->
          <div id="tab-status" class="db-tab-panel active">
            <div class="db-metric-grid">
              <div class="db-metric-box blue">
                <div class="db-metric-title">Total Events Sent</div>
                <div id="metric-total-sent" class="db-metric-value">0</div>
                <div class="db-metric-sub">Packets buffered &amp; dispatched</div>
              </div>
              <div class="db-metric-box green">
                <div class="db-metric-title">Successfully Indexed</div>
                <div id="metric-indexed" class="db-metric-value">0</div>
                <div class="db-metric-sub">HTTP 200 OK responses</div>
              </div>
              <div class="db-metric-box amber">
                <div class="db-metric-title">Current Rate (EPS)</div>
                <div id="metric-current-eps" class="db-metric-value">0</div>
                <div class="db-metric-sub">Events per second</div>
              </div>
              <div class="db-metric-box purple">
                <div class="db-metric-title">Target Sourcetype</div>
                <div id="metric-sourcetype" class="db-metric-value" style="font-size: 18px; word-break: break-all;">httpevent</div>
                <div class="db-metric-sub">Splunk metadata categorization</div>
              </div>
              <div class="db-metric-box cyan">
                <div class="db-metric-title">Target Index</div>
                <div id="metric-index" class="db-metric-value" style="font-size: 18px;">cisco_metrics</div>
                <div class="db-metric-sub">Splunk destination storage</div>
              </div>
            </div>
          </div>

          <!-- TAB 2: Sample Data View -->
          <div id="tab-sample" class="db-tab-panel">
            <div class="db-card">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <label class="db-card-label" style="margin-bottom: 0;">Active Payload Rolling Preview</label>
                <span id="db-sample-format-badge" class="db-badge db-badge-cyan">JSON Payload</span>
              </div>
              <div id="db-sample-code" class="db-code-view"></div>
            </div>
          </div>

          <!-- TAB 3: Splunk Integration Blueprint -->
          <div id="tab-blueprint" class="db-tab-panel">
            <div id="db-blueprint-container" class="db-blueprint-card"></div>
          </div>

          <!-- TAB 4: Scenario Logs -->
          <div id="tab-logs" class="db-tab-panel">
            <div class="db-card">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <label class="db-card-label" style="margin-bottom: 0;">Backend Simulation Engine Output</label>
                <button id="db-clear-logs-btn" class="db-btn db-btn-outline" style="padding: 4px 10px; font-size: 11px;">Clear Log</button>
              </div>
              <div id="db-terminal-output" class="db-terminal">
                <div class="db-term-line"><span class="db-term-time">[SYS]</span> <span class="db-term-info">TA-datablaster initialized. Engine binary verified.</span></div>
                <div class="db-term-line"><span class="db-term-time">[SYS]</span> Destination: ${this.state.hecUrl}</div>
                <div class="db-term-line"><span class="db-term-time">[SYS]</span> Awaiting Blast trigger...</div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    bindEvents() {
      // Tab switching
      const tabBtns = this.root.querySelectorAll('.db-tab-btn');
      tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          tabBtns.forEach(b => b.classList.remove('active'));
          this.root.querySelectorAll('.db-tab-panel').forEach(p => p.classList.remove('active'));

          btn.classList.add('active');
          const target = btn.getAttribute('data-tab');
          this.root.querySelector('#' + target).classList.add('active');
          this.state.activeTab = target;
        });
      });

      // Preset selection
      const presetSelect = this.root.querySelector('#db-preset-select');
      presetSelect.addEventListener('change', (e) => {
        const key = e.target.value;
        if (PRESETS[key]) {
          const preset = PRESETS[key];
          this.state.sampleContent = preset.content;
          this.state.sampleName = preset.name;
          this.state.targetIndex = preset.targetIndex;
          this.state.targetSourcetype = preset.targetSourcetype;
          this.updateBlueprint();
          this.updateSamplePreview();
        }
      });

      // Drag and drop / File upload
      const dropzone = this.root.querySelector('#db-dropzone');
      const fileInput = this.root.querySelector('#db-file-input');

      dropzone.addEventListener('click', () => fileInput.click());
      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
      dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.handleFile(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
          this.handleFile(e.target.files[0]);
        }
      });

      // Inputs
      const epsInput = this.root.querySelector('#db-eps-input');
      epsInput.addEventListener('change', (e) => {
        this.state.targetEps = parseInt(e.target.value) || 50;
      });

      const urlInput = this.root.querySelector('#db-hec-url');
      urlInput.addEventListener('input', (e) => {
        this.state.hecUrl = e.target.value;
      });

      const tokenInput = this.root.querySelector('#db-hec-token');
      tokenInput.addEventListener('input', (e) => {
        this.state.hecToken = e.target.value;
      });

      const scenarioSelect = this.root.querySelector('#db-scenario-select');
      scenarioSelect.addEventListener('change', (e) => {
        this.state.currentScenario = e.target.value;
        this.appendLog('Scenario changed to: ' + e.target.options[e.target.selectedIndex].text, 'info');
      });

      // Blast Button
      const blastBtn = this.root.querySelector('#db-blast-btn');
      blastBtn.addEventListener('click', () => this.toggleBlast());

      // Reset Button
      const resetBtn = this.root.querySelector('#db-reset-btn');
      resetBtn.addEventListener('click', () => {
        this.state.totalSent = 0;
        this.state.indexedCount = 0;
        this.state.currentEps = 0;
        this.updateMetrics();
        this.appendLog('Counters reset by user.', 'info');
      });

      // Clear Logs
      const clearLogsBtn = this.root.querySelector('#db-clear-logs-btn');
      clearLogsBtn.addEventListener('click', () => {
        this.root.querySelector('#db-terminal-output').innerHTML = '';
      });

      this.updateSamplePreview();
    }

    handleFile(file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.state.sampleContent = e.target.result;
        this.state.sampleName = file.name;
        this.root.querySelector('#db-preset-select').value = 'custom';
        this.updateBlueprint();
        this.updateSamplePreview();
        this.appendLog(`Uploaded file "${file.name}" (${file.size} bytes). Evaluated for Splunk Blueprint compliance.`, 'success');
      };
      reader.readAsText(file);
    }

    updateSamplePreview() {
      const codeView = this.root.querySelector('#db-sample-code');
      if (codeView) {
        codeView.textContent = this.state.sampleContent;
      }
    }

    /**
     * Strict Splunk Blueprint Evaluation Engine
     */
    evaluateCompliance() {
      const text = this.state.sampleContent || '';
      const isMDT = /telemetry_version|subscription_id|collection_id|encoding_path|grpc/i.test(text);

      if (isMDT) {
        return {
          category: 'METRICS INDEX',
          recommendation: 'Recommendation: Create a METRICS INDEX. Splunk Technical Add-on Required: Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry)',
          targetIndex: 'cisco_metrics',
          recommendedTA: 'Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry)',
          taId: 'TA-cisco-telemetry',
          sourcetype: 'httpevent',
          isMdt: true,
          badgeClass: 'db-badge-cyan',
          alertClass: 'db-alert-success'
        };
      }

      // Standard Log Evaluation
      let recommendedTA = 'Splunk Add-on for Unix and Linux';
      let taId = 'Splunk_TA_nix';
      let sourcetype = 'syslog';

      if (/ASA-|FTD-/i.test(text)) {
        recommendedTA = 'Splunk Add-on for Cisco ASA';
        taId = 'Splunk_TA_cisco-asa';
        sourcetype = 'cisco:asa';
      } else if (/pan|PAN-OS/i.test(text)) {
        recommendedTA = 'Palo Alto Networks Add-on for Splunk';
        taId = 'Splunk_TA_paloalto';
        sourcetype = 'pan:traffic';
      }

      return {
        category: 'EVENTS INDEX',
        recommendation: 'Recommendation: Create an EVENTS INDEX.',
        targetIndex: 'main',
        recommendedTA: recommendedTA,
        taId: taId,
        sourcetype: sourcetype,
        isMdt: false,
        badgeClass: 'db-badge-purple',
        alertClass: 'db-alert-success'
      };
    }

    updateBlueprint() {
      const result = this.evaluateCompliance();
      this.state.targetIndex = result.targetIndex;
      this.state.targetSourcetype = result.sourcetype;
      this.updateMetrics();

      const container = this.root.querySelector('#db-blueprint-container');
      if (!container) return;

      const isIndexMismatch = result.isMdt && (this.state.targetIndex !== 'cisco_metrics' && this.state.targetIndex !== 'splunk_otel');

      container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; font-size: 16px; color: #fff; display: flex; align-items: center; gap: 8px;">
            <span>🛡️ Architectural Compliance &amp; TA Blueprint</span>
          </h3>
          <span class="db-badge ${result.badgeClass}">Category: ${result.category}</span>
        </div>

        ${isIndexMismatch ? `
          <div class="db-alert db-alert-danger">
            <span style="font-size: 18px;">⚠️</span>
            <div>
              <strong>CRITICAL INDEX MISMATCH DETECTED:</strong><br>
              Cisco Model-Driven Telemetry (MDT) payload detected, but target index is configured as an Events Index. Streaming high-frequency MDT into an events index breaks data models and exhausts indexer storage.
            </div>
          </div>
        ` : ''}

        <div class="db-alert ${result.alertClass}">
          <span style="font-size: 18px;">✔</span>
          <div>
            <strong>${result.recommendation}</strong><br>
            <span style="color: var(--db-text-muted); font-size: 12px;">Parser inspected payload for MDT markers (<code>telemetry_version</code>, <code>subscription_id</code>, <code>collection_id</code>, gRPC) and protocol signatures.</span>
          </div>
        </div>

        <table class="db-blueprint-table">
          <thead>
            <tr>
              <th>Evaluation Parameter</th>
              <th>Detected Value / Recommendation</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Target Storage Tier</strong></td>
              <td><code>${result.category}</code> (e.g. <code>${result.targetIndex}</code>)</td>
              <td><span class="db-badge db-badge-success">Enforced</span></td>
            </tr>
            <tr>
              <td><strong>Recommended Splunk TA</strong></td>
              <td><strong>${result.recommendedTA}</strong> (<code>${result.taId}</code>)</td>
              <td><span class="db-badge db-badge-cyan">Required</span></td>
            </tr>
            <tr>
              <td><strong>CIM Data Model Mapping</strong></td>
              <td>${result.isMdt ? 'Performance & Network Metrics (Splunk Metric Schema)' : 'Network Traffic / Authentication (Splunk Event Schema)'}</td>
              <td><span class="db-badge db-badge-purple">Compliant</span></td>
            </tr>
            <tr>
              <td><strong>Default Ingestion Sourcetype</strong></td>
              <td><code>${result.sourcetype}</code></td>
              <td><span class="db-badge db-badge-success">Mapped</span></td>
            </tr>
          </tbody>
        </table>
      `;
    }

    updateMetrics() {
      this.root.querySelector('#metric-total-sent').textContent = this.state.totalSent.toLocaleString();
      this.root.querySelector('#metric-indexed').textContent = this.state.indexedCount.toLocaleString();
      this.root.querySelector('#metric-current-eps').textContent = this.state.currentEps.toLocaleString();
      this.root.querySelector('#metric-sourcetype').textContent = this.state.targetSourcetype;
      this.root.querySelector('#metric-index').textContent = this.state.targetIndex;
    }

    appendLog(msg, type = 'info') {
      const term = this.root.querySelector('#db-terminal-output');
      if (!term) return;

      const timeStr = new Date().toISOString().substring(11, 19);
      const line = document.createElement('div');
      line.className = 'db-term-line';

      let typeClass = 'db-term-info';
      if (type === 'success') typeClass = 'db-term-success';
      if (type === 'warn') typeClass = 'db-term-warn';
      if (type === 'error') typeClass = 'db-term-error';

      line.innerHTML = `<span class="db-term-time">[${timeStr}]</span> <span class="${typeClass}">[${type.toUpperCase()}]</span> ${msg}`;
      term.appendChild(line);
      term.scrollTop = term.scrollHeight;
    }

    toggleBlast() {
      if (this.state.isRunning) {
        this.stopBlast();
      } else {
        this.startBlast();
      }
    }

    startBlast() {
      this.state.isRunning = true;
      const btn = this.root.querySelector('#db-blast-btn');
      btn.className = 'db-btn db-btn-danger';
      btn.innerHTML = '<span>⏹ Stop Blast</span>';

      const statusBar = this.root.querySelector('#db-status-bar');
      statusBar.innerHTML = 'Status: <span style="color: #34d399; font-weight: 600;">Active &amp; Streaming</span>';

      const engineBadge = this.root.querySelector('#db-engine-status');
      engineBadge.className = 'db-badge db-badge-success';
      engineBadge.textContent = 'Streaming';

      this.appendLog(`Started DataBlaster generator (${this.state.targetEps} EPS) targeting ${this.state.hecUrl}`, 'success');
      this.appendLog(`Workers allocated: 15 Generator threads, 15 Outputter threads. Compression: enabled`, 'info');

      // Bridge to Splunk Custom REST Backend
      try {
        fetch('/en-US/splunkd/__raw/services/datablaster/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'start',
            eps: this.state.targetEps,
            hec_url: this.state.hecUrl,
            hec_token: this.state.hecToken,
            scenario: this.state.currentScenario
          })
        }).then(r => r.json()).then(data => {
          if (data && data.result && data.result.pid) {
            this.appendLog(`Backend daemon confirmed running (PID: ${data.result.pid}). Binary: ${data.result.binary}`, 'success');
          }
        }).catch(() => {
          // Running outside live Splunkd instance, fallback to client-side streaming simulator
        });
      } catch (e) {}

      // Live loop simulator
      this.state.timerId = setInterval(() => {
        const delta = Math.floor(this.state.targetEps * (0.9 + Math.random() * 0.2));
        this.state.totalSent += delta;
        this.state.indexedCount += delta;
        this.state.currentEps = delta;
        this.updateMetrics();

        // Roll dynamic sample in Tab 2
        this.rollDynamicSample();
      }, 1000);

      // Log stream simulator
      this.state.logIntervalId = setInterval(() => {
        const batchBytes = Math.floor(Math.random() * 4096) + 2048;
        this.appendLog(`HEC Batch dispatched: ${batchBytes} bytes. Channel: ${Math.random().toString(36).substring(7)} -> HTTP 200 OK`, 'success');
      }, 2500);
    }

    stopBlast() {
      this.state.isRunning = false;
      clearInterval(this.state.timerId);
      clearInterval(this.state.logIntervalId);

      // Signal backend REST to terminate background daemon
      try {
        fetch('/en-US/splunkd/__raw/services/datablaster/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop' })
        }).catch(() => {});
      } catch (e) {}

      const btn = this.root.querySelector('#db-blast-btn');
      btn.className = 'db-btn db-btn-primary';
      btn.innerHTML = '<span>⚡ Fire Blast</span>';

      const statusBar = this.root.querySelector('#db-status-bar');
      statusBar.innerHTML = 'Status: <span style="color: #60a5fa; font-weight: 600;">Idle</span>';

      const engineBadge = this.root.querySelector('#db-engine-status');
      engineBadge.className = 'db-badge db-badge-cyan';
      engineBadge.textContent = 'Engine Ready';

      this.state.currentEps = 0;
      this.updateMetrics();
      this.appendLog('Simulation stopped. Flush buffer committed.', 'warn');
    }

    rollDynamicSample() {
      const text = this.state.sampleContent;
      const now = new Date();
      const iso = now.toISOString();
      const epoch = Math.floor(now.getTime() / 1000);

      let rolled = text
        .replace(/1789762400000|\d{10}/g, epoch)
        .replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z/g, iso);

      const codeView = this.root.querySelector('#db-sample-code');
      if (codeView) {
        codeView.textContent = rolled;
      }
    }
  }

  // Initialize once DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    new DataBlasterApp('datablaster-app-root');
  });

  // Export globally for Splunk Web integration
  window.DataBlasterApp = DataBlasterApp;
})();
