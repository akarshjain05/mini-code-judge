// ── main.js — loaded last, wires all modules together ────────────────

// Apply saved theme immediately (before first paint)
initTheme();

// Populate page loaders now that all page modules are defined
Object.assign(PAGE_LOADERS, {
  history:     loadHistory,
  problems:    loadProblems,
  dashboard:   loadDashboard,
  admin:       loadAdminDashboard,
  analytics:   loadAnalytics,
  contests:    loadContests,
  account:     loadAccount,
  leaderboard: loadLeaderboard,
  settings:    loadSettings,
});

// popstate — browser back/forward
window.addEventListener('popstate', () => handleHashNav());

// App startup
window.onload = async () => {
  updateAuthUI();
  fetchCurrentUser();
  initGoogleSignIn();

  showPageLoader();
  try {
    // Always pre-load problems list and dashboard data in the background;
    // handleHashNav() then activates the correct page for the URL hash.
    await Promise.all([loadProblems(), loadDashboard()]);
  } catch(e) { console.error('Initial load error:', e); }
  finally { hidePageLoader(); }

  // Navigate to the hash AFTER data is loaded
  if (window.location.hash) {
    handleHashNav();
  }
};
