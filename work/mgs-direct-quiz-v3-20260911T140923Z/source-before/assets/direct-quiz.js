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

  function init() {
    if (!root || !root.document || !root.location) return;
    var links = root.document.querySelectorAll('[data-mgs-dq-cta]');
    Array.prototype.forEach.call(links, function (link) {
      var base = link.getAttribute('href') || '';
      link.setAttribute('href', mergeUrl(base, root.location.href));
    });
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
