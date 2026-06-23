// ── Navigation & Router ─────────────────────────────────────────────
// Startup & PAGE_LOADERS are in main.js (loaded last)

function initGoogleSignIn() {
  if (!window.google || !google.accounts || !google.accounts.id) return;
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleCredentialResponse,
  });
  const target = document.getElementById('googleSignInDiv');
  if (target) {
    google.accounts.id.renderButton(target, { theme: 'outline', size: 'large', width: 300, text: 'continue_with' });
  }
}

async function handleGoogleCredentialResponse(response) {
  const err = document.getElementById('loginErr');
  err.className = 'alert'; err.textContent = '';
  try {
    const res = await fetch(`${API}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: response.credential }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showAlert(err, data.detail || 'Google sign-in failed', 'error');
      return;
    }

    if (data.needs_setup) {
      pendingGoogleSetupToken = data.setup_token;
      document.getElementById('googleSetupUsername').value = data.suggested_username || '';
      document.getElementById('googleSetupPassword').value = '';
      const setupErr = document.getElementById('googleSetupErr');
      setupErr.className = 'alert'; setupErr.textContent = '';
      showGoogleSetupForm();
      return;
    }

    await finishLogin(data.access_token);
  } catch (e) {
    showAlert(err, 'Cannot reach API — is the server running? (or CORS blocked)', 'error');
  }
}

async function finishLogin(accessToken) {
  token = accessToken;
  const meRes = await fetch(`${API}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
  const me = await meRes.json();
  username = me.username;
  localStorage.setItem('jwt', token);
  localStorage.setItem('username', username);
  closeAuthModal(); updateAuthUI(); fetchCurrentUser();
  // Dashboard has no nav item anymore (only reachable via the logo, first
  // page load, or login) — so land there with fresh account data on login.
  await goTo('dashboard');
}

function showGoogleSetupForm() {
  document.getElementById('authTabs').style.display = 'none';
  document.getElementById('googleButtonWrap').style.display = 'none';
  document.getElementById('googleDivider').style.display = 'none';
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('googleSetupForm').style.display = 'block';
}

function hideGoogleSetupForm() {
  document.getElementById('authTabs').style.display = 'flex';
  document.getElementById('googleButtonWrap').style.display = 'flex';
  document.getElementById('googleDivider').style.display = 'flex';
  document.getElementById('googleSetupForm').style.display = 'none';
  switchAuthTab('login');
}

async function completeGoogleSignup() {
  const u = document.getElementById('googleSetupUsername').value.trim();
  const p = document.getElementById('googleSetupPassword').value;
  const err = document.getElementById('googleSetupErr');
  err.className = 'alert'; err.textContent = '';

  if (!pendingGoogleSetupToken) {
    showAlert(err, 'Setup session expired. Please click "Sign in with Google" again.', 'error');
    return;
  }
  if (!u || !p) {
    showAlert(err, 'Please choose a username and password.', 'error');
    return;
  }

  try {
    const res = await fetch(`${API}/auth/complete-google-signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ setup_token: pendingGoogleSetupToken, username: u, password: p }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      let msg = 'Could not complete sign up';
      if (typeof data.detail === 'string') msg = data.detail;
      else if (Array.isArray(data.detail) && data.detail.length) msg = data.detail[0].msg;
      showAlert(err, msg, 'error');
      return;
    }
    pendingGoogleSetupToken = null;
    await finishLogin(data.access_token);
    closeAuthModal();
    openOnboarding(); // new Google user: collect display name + DOB
  } catch (e) {
    showAlert(err, 'Cannot reach API — is the server running?', 'error');
  }
}

// ── Navigation ─────────────────────────────────────────────────────
function showPageLoader() { document.getElementById('pageLoader').style.display = 'flex'; }
function hidePageLoader() { document.getElementById('pageLoader').style.display = 'none'; }

// Populated in main.js after all page modules are loaded
const PAGE_LOADERS = {};

function getCurrentPageId() {
  const el = document.querySelector('.page.active');
  return el ? el.id.replace('page-', '') : null;
}

async function refreshCurrentPage() {
  const id = getCurrentPageId();
  const fn = PAGE_LOADERS[id];
  if (!fn) return;
  showPageLoader();
  try { await fn(); }
  catch(e) { console.error('Refresh error:', e); }
  finally { hidePageLoader(); }
}

async function goTo(page, pushState = true) {
  if (!token && ['history','analytics','contests','account','leaderboard'].includes(page)) { openAuthModal(); return; }
  const pageEl = document.getElementById('page-' + page);
  if (!pageEl) return;

  const loaderFn = PAGE_LOADERS[page];

  if (loaderFn) showPageLoader();

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  pageEl.classList.add('active');
  const items = document.querySelectorAll('.nav-item');
  const map = { problems: 0, submit: 1, history: 2 };
  if (map[page] !== undefined) items[map[page]].classList.add('active');
  if (pushState) history.pushState({ page }, '', '#' + page);

  if (loaderFn) {
    try { await loaderFn(); }
    catch(e) { console.error('Page load error:', e); }
    finally { hidePageLoader(); }
  }
}

function goToProblem(problemObj) {
  openProblem(problemObj);
  history.pushState({ page: 'submit', problem_id: problemObj.id }, '', '#problem/' + problemObj.id);
}

function handleHashNav() {
  const hash = window.location.hash.replace('#', '');
  if (!hash || hash === 'dashboard') { goTo('dashboard', false); return; }
  if (hash.startsWith('reset-password/')) {
    const resetToken = hash.split('/').slice(1).join('/');
    if (resetToken) openResetPasswordModal(decodeURIComponent(resetToken));
    return;
  }
  if (hash.startsWith('contest/')) {
    const id = parseInt(hash.split('/')[1]);
    if (id && token) { goTo('contests', false); openContest(id); }
    else if (id) { openAuthModal(); }
    return;
  }
  if (hash.startsWith('problem/')) {
    const id = parseInt(hash.split('/')[1]);
    if (id) {
      goTo('problems', false);
      fetch(`${API}/problems`).then(r => r.json()).then(problems => {
        const p = problems.find(p => p.id === id);
        if (p) { openProblem(p); history.replaceState({ page: 'submit', problem_id: id }, '', '#problem/' + id); }
      }).catch(() => {});
    }
    return;
  }
  if (hash.startsWith('submission/')) {
    const id = parseInt(hash.split('/')[1]);
    if (id && token) {
      goTo('history', false);
      loadHistory().then(() => {
        if (window._submissionsCache && window._submissionsCache[id]) openSubmissionViewer(id);
      });
    } else if (id) { openAuthModal(); }
    return;
  }
  const validPages = ['dashboard','problems','submit','history','analytics','account','leaderboard','contests','admin','addproblem','settings'];
  if (validPages.includes(hash)) goTo(hash, false);
  else goTo('dashboard', false);
}
