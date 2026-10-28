(() => {
  document.body.addEventListener('htmx:afterSwap', event => {
    if (event.target.matches('.favorite-form')) {
      document.getElementById('action-status').textContent = event.target.querySelector('button').getAttribute('aria-pressed') === 'true' ? 'File saved.' : 'File removed from saved.';
    }
  });
})();
