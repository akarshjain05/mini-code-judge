// ── Navigation & Router ─────────────────────────────────────────────
// Startup & PAGE_LOADERS are in main.js (loaded last)

function initGoogleSignIn(retries = 10) {
  // Always render the visual button immediately so the UI doesn't look broken
  const wrap = document.getElementById('googleButtonWrap');
  if (wrap && !wrap.innerHTML.includes('btn-google-signin')) {
    wrap.innerHTML = `
      <button class="btn-google-signin" onclick="triggerGoogleSignIn()">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Continue with Google
      </button>
      <div id="googleSignInDiv" style="display:none"></div>`;
  }

  // If the Google library isn't loaded yet, keep trying in the background
  if (!window.google || !google.accounts || !google.accounts.id) {
    if (retries > 0) setTimeout(() => initGoogleSignIn(retries - 1), 500);
    return;
  }

  // Once loaded, initialize the actual API
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleCredentialResponse,
  });

  // Render tiny hidden button so Google's credential callback still works
  setTimeout(() => {
    const hidden = document.getElementById('googleSignInDiv');
    if (hidden && window.google) google.accounts.id.renderButton(hidden, { size: 'small', width: 1 });
  }, 100);
}

function triggerGoogleSignIn() {
  if (window.google && google.accounts && google.accounts.id) {
    google.accounts.id.prompt();
  } else {
    showAlert(document.getElementById('loginErr'), 'Google Sign-In is blocked by your browser or adblocker.', 'error');
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

async function finishLogin(jwt) {
  if (jwt) {
    token = jwt;
    localStorage.setItem('token', jwt);
  }
  const meRes = await fetch(`${API}/auth/me`, { headers: {} });
  const me = await meRes.json();
  username = me.username;
  
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
  if (!u) {
    showAlert(err, 'Please choose a username.', 'error');
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
  if (window.globalAbortController) {
    window.globalAbortController.abort();
    window.globalAbortController = new AbortController();
  }
  if (!token && ['history','analytics','contests','account','leaderboard'].includes(page)) { openAuthModal(); return; }
  const pageEl = document.getElementById('page-' + page);
  if (!pageEl) return;

  const isSamePage = (getCurrentPageId() === page);
  const skipLoad = (!pushState && isSamePage);

  const loaderFn = PAGE_LOADERS[page];

  if (loaderFn && !skipLoad) showPageLoader();

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  pageEl.classList.add('active');
  const items = document.querySelectorAll('.nav-item');
  const map = { problems: 0, submit: 1, history: 2 };
  if (map[page] !== undefined) items[map[page]].classList.add('active');
  if (pushState) history.pushState({ page }, '', '#' + page);

  if (loaderFn && !skipLoad) {
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
  
  if (!hash.startsWith('submission/') && !hash.startsWith('admin')) {
    const cv = document.getElementById('codeViewerModal');
    if (cv) cv.style.display = 'none';
  }

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
      const openById = (problems) => {
        const p = problems.find(p => p.id === id);
        if (p) {
          openProblem(p);
          history.replaceState({ page: 'submit', problem_id: id }, '', '#problem/' + id);
        }
      };
      // Use already-loaded problems if available (avoids a duplicate fetch
      // and avoids silently failing on a cold/slow backend)
      if (_allProblems && _allProblems.length) {
        openById(_allProblems);
      } else {
        fetch(`${API}/problems`)
          .then(r => r.json())
          .then(openById)
          .catch(() => {
            const vbox = document.getElementById('verdictBox');
            if (vbox) vbox.classList.remove('show');
          });
      }
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
  const validPages = ['dashboard','problems','submit','history','analytics','account','leaderboard','contests','admin','addproblem','settings','terms','privacy','faq','help'];
  if (validPages.includes(hash)) goTo(hash, false);
  else goTo('dashboard', false);
}
