(function (root) {
  'use strict';

  var EXCLUDED = { page_id: true, p: true, mgs_dq_country: true, mgs_dq_slug: true };

  function mergeUrl(base, source) {
    if (!base) return '';
    try {
      var destination = new URL(base);
      var current = new URL(source || (root && root.location ? root.location.href : ''));
      current.searchParams.forEach(function (value, key) {
        if (EXCLUDED[key] || destination.searchParams.has(key)) return;
        destination.searchParams.append(key, value);
      });
      return destination.toString();
    } catch (error) {
      return base;
    }
  }

  function initLinks() {
    if (!root || !root.document || !root.location) return;
    var links = root.document.querySelectorAll('[data-mgs-dq-cta]');
    Array.prototype.forEach.call(links, function (link) {
      var base = link.getAttribute('href') || '';
      link.setAttribute('href', mergeUrl(base, root.location.href));
    });
  }

  function initCountdown() {
    if (!root || !root.document) return;
    var output = root.document.querySelector('[data-mgs-dq-countdown]');
    if (!output) return;

    function render() {
      var now = new Date();
      var end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0);
      var seconds = Math.max(0, Math.floor((end.getTime() - now.getTime()) / 1000));
      var hours = Math.floor(seconds / 3600);
      var minutes = Math.floor((seconds % 3600) / 60);
      var remainder = seconds % 60;
      output.textContent = [hours, minutes, remainder].map(function (value) {
        return String(value).padStart(2, '0');
      }).join(':');
    }

    render();
    root.setInterval(render, 1000);
  }

  function initDisclaimer() {
    if (!root || !root.document) return;
    var toggle = root.document.querySelector('[data-mgs-dq-disclaimer-toggle]');
    var box = root.document.querySelector('[data-mgs-dq-disclaimer-box]');
    if (!toggle || !box) return;

    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      box.hidden = expanded;
    });
  }

  function init() {
    initLinks();
    initCountdown();
    initDisclaimer();
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { mergeUrl: mergeUrl };
  }
  if (root && root.document) {
    if (root.document.readyState === 'loading') {
      root.document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }
})(typeof window !== 'undefined' ? window : null);
