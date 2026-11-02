/*
 * Splunk App: NetSpout PulseForge (netspout)
 * View Script: netspout_canvas.js
 * Canvas & Telemetry Orchestrator Controller
 * Author: Mahamudul Chowdhury <machowdhury@yahoo.com>
 */

require([
  'jquery',
  'splunkjs/mvc',
  'splunkjs/mvc/simplexml/ready!'
], function($, mvc) {
  'use strict';

  function injectCanvas() {
    var container = $('#netspout-container');
    if (!container.length) {
      setTimeout(injectCanvas, 100);
      return;
    }

    // Avoid duplicate injection
    if ($('#netspout-canvas-frame').length) {
      return;
    }

    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    // API calls go through the app's authenticated REST gateway on this origin (no backend port in the browser).
    // The view name selects the React route: Command Center = home, Use Case Explorer = #/explore.
    var view = (window.location.pathname.match(/\/app\/netspout\/([^/?#]+)/) || [])[1] || '';
    var route = { pulseforge_command_center: '#/', use_case_explorer: '#/explore' }[view] || '';
    var canvasUrl = '/' + locale + '/static/app/netspout/dist/index.html' + route;

    var iframe = $('<iframe>', {
      id: 'netspout-canvas-frame',
      src: canvasUrl,
      allow: 'clipboard-read; clipboard-write; fullscreen',
      css: {
        width: '100%',
        height: 'calc(100vh - 110px)',
        minHeight: '850px',
        border: 'none',
        display: 'block',
        background: '#0B0F19'
      }
    });

    container.empty().append(iframe);
  }

  // Handle window resize dynamically so canvas always occupies full height
  $(window).on('resize', function() {
    var frame = $('#netspout-canvas-frame');
    if (frame.length) {
      var availableHeight = Math.max(850, $(window).height() - 110);
      frame.css('height', availableHeight + 'px');
      $('#netspout-container').css('min-height', availableHeight + 'px');
    }
  });

  // Inject once DOM is ready
  injectCanvas();
});
