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

  // Handle email verification link (#verify-email/<token>)
  if (hash.startsWith('#verify-email/')) {
    const verifyToken = hash.replace('#verify-email/', '').trim();
    history.replaceState(null, '', window.location.pathname);
    try {
      const res = await fetch(`${API}/auth/verify-email/${verifyToken}`);
      const data = await res.json();
      openAuthModal();
      const errEl = document.getElementById('loginErr');
      if (res.ok) {
        errEl.className = 'alert success';
        errEl.textContent = '✓ ' + (data.message || 'Email verified! You can now log in.');
      } else {
        errEl.className = 'alert error';
        errEl.textContent = data.detail || 'Verification link is invalid or expired.';
      }
    } catch(e) {
      openAuthModal();
    }
    showPageLoader();
    try { await Promise.all([loadProblems(), loadDashboard()]); } catch(e) {}
    finally { hidePageLoader(); }
    return;
  }

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