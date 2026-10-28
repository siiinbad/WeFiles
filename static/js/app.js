(() => {
  const root = document.documentElement;
  const media = matchMedia('(prefers-color-scheme: dark)');
  function applyTheme(preference) {
    root.dataset.themePreference = preference;
    root.dataset.bsTheme = preference === 'dark' || (preference === 'system' && media.matches) ? 'dark' : 'light';
    document.querySelectorAll('.theme-toggle').forEach(button => {
      button.title = `Theme: ${preference}. Click to change.`;
      button.setAttribute('aria-label', button.title);
    });
  }
  applyTheme(root.dataset.themePreference || 'system');
  media.addEventListener('change', () => applyTheme(root.dataset.themePreference));
  document.querySelectorAll('.theme-toggle').forEach(button => button.addEventListener('click', () => {
    const choices = ['system', 'light', 'dark'];
    const next = choices[(choices.indexOf(root.dataset.themePreference) + 1) % choices.length];
    try { localStorage.setItem('wefiles-theme', next); } catch (_) { /* Optional preference. */ }
    applyTheme(next);
    document.getElementById('action-status').textContent = `Color theme: ${next}.`;
  }));
  const menu = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('navigation');
  const mobileLayout = matchMedia('(max-width:1023px)');
  function syncNavigation() { if (sidebar) sidebar.inert = mobileLayout.matches && !sidebar.classList.contains('is-open'); }
  function closeMenu() { sidebar?.classList.remove('is-open'); menu?.setAttribute('aria-expanded', 'false'); syncNavigation(); }
  syncNavigation();
  mobileLayout.addEventListener('change', syncNavigation);
  menu?.addEventListener('click', () => {
    const open = sidebar.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(open));
    syncNavigation();
    if (open) sidebar.querySelector('a')?.focus();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && sidebar?.classList.contains('is-open')) { closeMenu(); menu.focus(); }
  });
  document.addEventListener('click', event => {
    if (sidebar?.classList.contains('is-open') && !sidebar.contains(event.target) && !menu.contains(event.target)) closeMenu();
  });
  document.addEventListener('submit', event => {
    const form = event.target;
    if (form.matches('[data-busy]')) {
      if (form.classList.contains('is-busy')) { event.preventDefault(); return; }
      form.classList.add('is-busy');
      form.setAttribute('aria-busy', 'true');
      form.querySelectorAll('button[type=submit]').forEach(button => { button.disabled = true; });
    }
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('form.is-busy').forEach(form => {
    form.classList.remove('is-busy'); form.removeAttribute('aria-busy');
    form.querySelectorAll('button[type=submit]').forEach(button => { button.disabled = false; });
  }));
  function showRequestError() {
    const error = document.getElementById('action-error');
    if (error) {
      error.hidden = false;
      error.textContent = 'That update could not be completed. Please refresh the page and try again.';
    }
  }
  document.body.addEventListener('htmx:responseError', showRequestError);
  document.body.addEventListener('htmx:sendError', showRequestError);
})();
