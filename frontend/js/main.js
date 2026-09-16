import { loadDashboard } from './pages/dashboard.js';
import { loadProblems } from './pages/problems.js';
import { loadHistory } from './pages/history.js';
import { loadContests } from './pages/contests.js';
import { loadAccount } from './pages/account.js';
import { showPageLoader, hidePageLoader, initGoogleSignIn, handleHashNav, PAGE_LOADERS } from './router.js';
import { initTheme, fetchCurrentUser, updateAuthUI } from './ui.js';
import { loadLeaderboard } from './pages/leaderboard.js';
import { openAuthModal, handleGitHubHashResult } from './auth.js';
import { loadSettings } from './pages/settings.js';
import { loadAnalytics } from './pages/analytics.js';
import { loadAdminDashboard } from './pages/admin.js';
import { state } from './state.js';
import { API, GOOGLE_CLIENT_ID, apiFetch } from './api.js';
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
  // Init sidebar state
  if (localStorage.getItem('sidebarCollapsed') === 'true') {
    const sidebar = document.getElementById('appSidebar');
    if (sidebar) sidebar.classList.add('collapsed');
  }

  // Always reset verdict box on startup — prevents stale state from previous session
  const vbox = document.getElementById('verdictBox');
  if (vbox) vbox.classList.remove('show');

  updateAuthUI();
  fetchCurrentUser();
  initGoogleSignIn();

  // Read hash ONCE at the top so it's available for all checks below
  const urlHash = window.location.hash;

  // Handle email verification link (#verify-email/<state.token>)
  if (urlHash.startsWith('#verify-email/')) {
    const verifyToken = urlHash.replace('#verify-email/', '').trim();
    history.replaceState(null, '', window.location.pathname);
    try {
      const res = await apiFetch(`${API}/auth/verify-email/${verifyToken}`);
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
    } catch(e) { openAuthModal(); }
    showPageLoader();
    try { await Promise.all([loadProblems(), loadDashboard()]); } catch(e) {}
    finally { hidePageLoader(); }
    return;
  }

  // Handle GitHub OAuth redirect result (hash set by backend after OAuth)
  if (urlHash.startsWith('#github-')) {
    await handleGitHubHashResult(urlHash);
    showPageLoader();
    try { await Promise.all([loadProblems(), loadDashboard()]); }
    catch(e) { console.error(e); }
    finally { hidePageLoader(); }
    return;
  }

  // Normal startup
  showPageLoader();
  try {
    await Promise.all([loadProblems(), loadDashboard()]);
  } catch(e) { console.error('Initial load error:', e); }
  finally { hidePageLoader(); }

  if (urlHash && !urlHash.startsWith('#github-') && !urlHash.startsWith('#verify-')) {
    handleHashNav();
  }
};
