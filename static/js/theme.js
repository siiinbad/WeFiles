(() => {
  let preference = 'system';
  try { preference = localStorage.getItem('wefiles-theme') || 'system'; } catch (_) { /* Storage can be disabled. */ }
  const dark = preference === 'dark' || (preference === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.bsTheme = dark ? 'dark' : 'light';
  document.documentElement.dataset.themePreference = preference;
})();
