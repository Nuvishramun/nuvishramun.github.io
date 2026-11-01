// Shared theme state. This runs before the page paints, on every page.
(() => {
  'use strict';
  const key = 'academic-theme';
  const preference = window.matchMedia('(prefers-color-scheme: dark)');
  const valid = theme => theme === 'light' || theme === 'dark';
  const read = () => {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  };
  const systemTheme = () => preference.matches ? 'dark' : 'light';
  const localFile = window.location.protocol === 'file:';
  let explicit = read();
  // file: pages do not consistently share localStorage across browsers.
  const carried = new URL(window.location.href).searchParams.get('theme');
  if (localFile && valid(carried)) {
    explicit = carried;
    try { localStorage.setItem(key, carried); } catch (_) {}
  }
  let current = valid(explicit) ? explicit : systemTheme();

  const syncLinks = () => {
    // GitHub Pages shares storage; only offline files need a URL fallback.
    if (!localFile) return;
    document.querySelectorAll('a[href]').forEach(anchor => {
      const raw = anchor.getAttribute('href');
      if (!raw || raw.startsWith('#')) return;
      const url = new URL(raw, window.location.href);
      if (url.protocol === 'file:' && url.pathname.endsWith('.html')) {
        url.searchParams.set('theme', current);
        anchor.setAttribute('href', url.href);
      }
    });
  };
  const apply = theme => {
    current = theme;
    document.documentElement.dataset.theme = theme;
    syncLinks();
    window.dispatchEvent(new CustomEvent('academic-theme-change', { detail: { theme } }));
  };
  const reconcile = () => {
    const saved = read();
    if (valid(saved)) explicit = saved;
    apply(valid(explicit) ? explicit : systemTheme());
  };
  window.academicTheme = {
    get: () => current,
    set: theme => {
      if (!valid(theme)) return;
      explicit = theme;
      try { localStorage.setItem(key, theme); } catch (_) {}
      // Keep an offline page's carried value current for reload/back navigation.
      if (localFile) {
        try {
          const url = new URL(window.location.href);
          url.searchParams.set('theme', theme);
          window.history.replaceState(null, '', url.href);
        } catch (_) {}
      }
      apply(theme);
    },
    syncLinks
  };
  // Changes made in another tab arrive here on the same hosted origin.
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    explicit = read();
    reconcile();
  });
  // Back/forward cache can restore an old DOM without re-running scripts.
  window.addEventListener('pageshow', reconcile);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') reconcile();
  });
  preference.addEventListener('change', () => {
    if (!valid(explicit)) apply(systemTheme());
  });
  apply(current);
})();
