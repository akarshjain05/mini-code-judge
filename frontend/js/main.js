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

  // Handle GitHub OAuth redirect result (hash set by backend after OAuth)
  const hash = window.location.hash;
  if (hash.startsWith('#github-')) {
    await handleGitHubHashResult(hash);
    // After handling, load dashboard normally
    showPageLoader();
    try { await Promise.all([loadProblems(), loadDashboard()]); }
    catch(e) { console.error(e); }
    finally { hidePageLoader(); }
    return;
  }

  showPageLoader();
  try {
    await Promise.all([loadProblems(), loadDashboard()]);
  } catch(e) { console.error('Initial load error:', e); }
  finally { hidePageLoader(); }

  if (window.location.hash && !window.location.hash.startsWith('#github-')) {
    handleHashNav();
  }
};