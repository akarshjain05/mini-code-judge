import { hideGoogleSetupForm, finishLogin } from './router.js';
import { loadSettings } from './pages/settings.js';
import { loadDashboard } from './pages/dashboard.js';
import { showAlert } from './ui.js';
import { state } from './state.js';
import { API, GOOGLE_CLIENT_ID, apiFetch } from './api.js';
// ── Auth Modal & Login/Register ────────────────────────────────────

export function openAuthModal() { document.getElementById('authModal').classList.add('show'); }
export function closeAuthModal() {
  document.getElementById('authModal').classList.remove('show');
  hideGoogleSetupForm();
  pendingGoogleSetupToken = null;
}

export function switchAuthTab(tab) {
  document.getElementById('loginForm').style.display        = tab === 'login'    ? 'block' : 'none';
  document.getElementById('registerForm').style.display     = tab === 'register' ? 'block' : 'none';
  document.getElementById('forgotPasswordForm').style.display = 'none';
  document.querySelectorAll('#authTabs .tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });
}

export const EYE_OPEN_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
export const EYE_OFF_SVG  = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

export async function doLogin() {
  const u = document.getElementById('loginUsername').value.trim();
  const p = document.getElementById('loginPassword').value;
  const err = document.getElementById('loginErr');
  err.className = 'alert'; err.textContent = '';
  try {
    const body = new URLSearchParams();
    body.append('username', u); body.append('password', p);
    const res = await apiFetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      let msg = 'Login failed';
      if (data.detail && typeof data.detail === 'string') msg = data.detail;
      else if (res.status === 401) msg = '❌ Incorrect state.username or password';
      else if (res.status === 429) msg = data.detail || '⚠ Too many attempts. Try again later.';
      else if (res.status === 422) msg = '⚠ Please fill in state.username and password';

      // Unverified email — show resend button
      if (res.status === 403) {
        showAlert(err, msg + ' <a href="#" onclick="resendVerificationEmail(event)" style="color:var(--accent);margin-left:6px">Resend email →</a>', 'error');
        err.innerHTML = err.textContent; // allow the link HTML
        err.innerHTML = `<span>${msg}</span> <a href="#" onclick="resendVerificationEmail(event)" style="color:var(--accent);margin-left:6px;font-size:12px">Resend email →</a>`;
      } else {
        showAlert(err, msg, 'error');
      }
      return;
    }
    await finishLogin(data.access_token);
  } catch(e) { showAlert(err, 'Cannot reach API — is the server running?', 'error'); }
}

export async function doRegister() {
  const u = document.getElementById('regUsername').value.trim();
  const e = document.getElementById('regEmail').value.trim();
  const p = document.getElementById('regPassword').value;
  const err = document.getElementById('registerErr');
  err.className = 'alert'; err.textContent = '';
  try {
    const res = await apiFetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u, email: e, password: p }),
    });
    const data = await res.json();
    if (!res.ok) {
      let msg = 'Registration failed';
      if (data.detail && typeof data.detail === 'string') msg = data.detail;
      else if (data.detail && Array.isArray(data.detail)) msg = data.detail.map(x => x.msg).join(', ');
      if (msg.includes('Username already')) msg = '❌ Username already taken';
      if (msg.includes('Email already')) msg = '❌ Email already registered — try logging in';
      showAlert(err, msg, 'error'); return;
    }
    showAlert(err, '✓ Account created! Logging you in…', 'success');
    // Auto-login then show onboarding
    setTimeout(async () => {
      document.getElementById('loginUsername').value = u;
      document.getElementById('loginPassword').value = p;
      const loginBody = new URLSearchParams();
      loginBody.append('username', u); loginBody.append('password', p);
      const loginRes = await apiFetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginBody.toString(),
      });
      const loginData = await loginRes.json().catch(() => ({}));
      if (loginRes.ok) {
        await finishLogin(loginData.access_token);
        closeAuthModal();
        openOnboarding(); // show name + DOB setup
      } else {
        switchAuthTab('login');
      }
    }, 800);
  } catch(e) { showAlert(err, 'Cannot reach API — is the server running?', 'error'); }
}

// ── Onboarding flow ───────────────────────────────────────────────────
export let _obFullName = '';

export function openOnboarding() {
  const initial = (state.username || '?')[0].toUpperCase();
  document.getElementById('obAvatar').textContent = initial;
  document.getElementById('obFullName').value = '';
  document.getElementById('obDob').value = '';
  document.getElementById('obDob').max = new Date().toISOString().split('T')[0];
  document.getElementById('obStep1Alert').className = 'alert';
  document.getElementById('obStep1Alert').textContent = '';
  document.getElementById('obStep2Alert').className = 'alert';
  document.getElementById('obStep2Alert').textContent = '';
  // Reset to step 1
  document.getElementById('ob-step-1').style.display = '';
  document.getElementById('ob-step-2').style.display = 'none';
  document.getElementById('ob-dot-1').style.background = 'var(--accent)';
  document.getElementById('ob-dot-2').style.background = 'var(--border)';
  document.getElementById('onboardingModal').style.display = 'flex';
  setTimeout(() => document.getElementById('obFullName').focus(), 100);
}

export function closeOnboarding() {
  document.getElementById('onboardingModal').style.display = 'none';
}

export function obNextStep() {
  const name = document.getElementById('obFullName').value.trim();
  const al = document.getElementById('obStep1Alert');
  al.className = 'alert'; al.textContent = '';
  _obFullName = name; // can be empty (skipped inline)
  // Move to step 2
  document.getElementById('ob-step-1').style.display = 'none';
  document.getElementById('ob-step-2').style.display = '';
  document.getElementById('ob-dot-1').style.background = 'var(--accent)';
  document.getElementById('ob-dot-2').style.background = 'var(--accent)';
  setTimeout(() => document.getElementById('obDob').focus(), 100);
}

export function obSkipStep() {
  _obFullName = '';
  obNextStep();
}

export async function obFinish(skipDob = false) {
  const dob = skipDob ? null : (document.getElementById('obDob').value || null);
  const payload = {};
  if (_obFullName) payload.full_name = _obFullName;
  if (dob) payload.date_of_birth = dob;

  if (Object.keys(payload).length > 0 && state.token) {
    try {
      await apiFetch(`${API}/auth/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch(e) { /* non-fatal, user can set later in settings */ }
  }

  closeOnboarding();
  // Refresh current page data
  if (state._settingsData) Object.assign(state._settingsData, payload);
  await loadDashboard();
}

// ── GitHub OAuth ──────────────────────────────────────────────────────
// Flow: open GitHub in same tab → backend /auth/github/redirect → back here
// with result in URL hash (#github-login, #github-setup, #github-error, #github-connected)

export let _githubSetupToken = null;

export function startGitHubOAuth(connectMode = false) {
  // Pass current JWT as state if connecting (so backend can identify the user)
  const state = connectMode && state.token ? `connect:${state.token}` : '';
  const url = `${API}/auth/github` + (state ? `?state=${encodeURIComponent(state)}` : '');
  window.location.href = url;
}

// Called from main.js on startup when URL hash contains github result
export async function handleGitHubHashResult(hash) {
  // Parse the hash: #github-login?state.token=xxx  |  #github-setup?setup_token=...
  //                 #github-error?msg=xxx    |  #github-connected
  const [hashPath, hashQuery] = hash.slice(1).split('?');
  const params = new URLSearchParams(hashQuery || '');

  // Clear the hash from URL so refreshing doesn't re-trigger
  history.replaceState(null, '', window.location.pathname);

  if (hashPath === 'github-login') {
    const jwt = params.get('token');
    if (jwt) {
      await finishLogin(jwt);
    }

  } else if (hashPath === 'github-setup') {
    // New GitHub user needs to pick a state.username
    _githubSetupToken = params.get('setup_token');
    const suggested   = params.get('suggested') || '';
    openAuthModal();
    showGitHubSetupForm(suggested);

  } else if (hashPath === 'github-error') {
    const msg = params.get('msg') || 'GitHub sign-in failed.';
    openAuthModal();
    const al = document.getElementById('githubSetupErr');
    if (al) { al.className = 'alert error'; al.textContent = decodeURIComponent(msg); }
    showGitHubSetupForm(null); // show the form area with the error

  } else if (hashPath === 'github-connected') {
    // Successfully connected GitHub to existing account
    const al = document.getElementById('sSocialAlert');
    if (al) { al.className = 'alert success'; al.textContent = 'GitHub connected successfully!'; }
    if (typeof loadSettings === 'function') await loadSettings();
  }
}

export function showGitHubSetupForm(suggestedUsername) {
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('googleSetupForm').style.display = 'none';
  document.getElementById('githubSetupForm').style.display = 'block';
  document.getElementById('googleButtonWrap').style.display = 'none';
  document.getElementById('githubSignInBtn').style.display = 'none';
  document.getElementById('googleDivider').style.display = 'none';
  const tabs = document.getElementById('authTabs');
  if (tabs) tabs.style.display = 'none';
  if (suggestedUsername !== null && suggestedUsername !== undefined) {
    const inp = document.getElementById('githubSetupUsername');
    if (inp) { inp.value = suggestedUsername; inp.focus(); }
  }
}

export async function completeGitHubSignup() {
  const uname = document.getElementById('githubSetupUsername').value.trim();
  const al    = document.getElementById('githubSetupErr');
  al.className = 'alert'; al.textContent = '';
  if (!uname)              { al.className = 'alert error'; al.textContent = 'Please choose a state.username.'; return; }
  if (!_githubSetupToken)  { al.className = 'alert error'; al.textContent = 'Session expired. Please try again.'; return; }
  try {
    const res = await apiFetch(`${API}/auth/complete-github-signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: uname, setup_token: _githubSetupToken, password: null }),
    });
    const data = await res.json();
    if (!res.ok) { al.className = 'alert error'; al.textContent = data.detail || 'Sign up failed.'; return; }
    _githubSetupToken = null;
    closeAuthModal();
    await finishLogin(data.access_token);
    openOnboarding();
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}

// Called from Settings → Social tab
export function handleGithubConnect() {
  startGitHubOAuth(true);
}

export async function resendVerificationEmail(e) {
  if (e) e.preventDefault();
  // User needs to be logged in to resend — try logging in first with stored creds
  // Since they're not verified, we can't issue a state.token. Instead call a public endpoint.
  // For now, show a message directing them to check spam or contact support.
  const err = document.getElementById('loginErr');
  err.className = 'alert';
  err.textContent = 'Sending verification email…';
  // Attempt re-send using a temporary session (login returns 403 but we need user id)
  // Best UX: re-send using email from the login field
  const loginField = document.getElementById('loginUsername');
  const email = loginField ? loginField.value.trim() : '';
  if (!email) {
    err.className = 'alert error';
    err.textContent = 'Please enter your state.username or email in the field above first.';
    return;
  }
  try {
    const res = await apiFetch(`${API}/auth/resend-verification-public`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: email }),
    });
    const data = await res.json();
    err.className = res.ok ? 'alert success' : 'alert error';
    err.textContent = res.ok ? '✓ Verification email sent! Check your inbox.' : (data.detail || 'Could not send email.');
  } catch(e) {
    err.className = 'alert error';
    err.textContent = 'Network error. Please try again.';
  }
}
window.openAuthModal = openAuthModal;
window.closeAuthModal = closeAuthModal;
window.switchAuthTab = switchAuthTab;
window.doLogin = doLogin;
window.doRegister = doRegister;
window.openOnboarding = openOnboarding;
window.closeOnboarding = closeOnboarding;
window.obNextStep = obNextStep;
window.obSkipStep = obSkipStep;
window.obFinish = obFinish;
window.startGitHubOAuth = startGitHubOAuth;
window.handleGitHubHashResult = handleGitHubHashResult;
window.showGitHubSetupForm = showGitHubSetupForm;
window.completeGitHubSignup = completeGitHubSignup;
window.handleGithubConnect = handleGithubConnect;
window.resendVerificationEmail = resendVerificationEmail;
