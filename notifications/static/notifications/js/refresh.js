(() => {
  // Custom events avoid eval-based HTMX trigger expressions under the CSP.
  window.setInterval(() => {
    if (document.visibilityState === 'visible') document.body.dispatchEvent(new Event('wefiles:refresh'));
  }, 5000);
})();
