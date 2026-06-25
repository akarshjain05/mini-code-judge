// ── Auth Modal & Login/Register ────────────────────────────────────

function openAuthModal() { document.getElementById('authModal').classList.add('show'); }
function closeAuthModal() {
  document.getElementById('authModal').classList.remove('show');
  hideGoogleSetupForm();
  pendingGoogleSetupToken = null;
}

function switchAuthTab(tab) {
  document.getElementById('loginForm').style.display        = tab === 'login'    ? 'block' : 'none';
  document.getElementById('registerForm').style.display     = tab === 'register' ? 'block' : 'none';
  document.getElementById('forgotPasswordForm').style.display = 'none';
  document.querySelectorAll('#authTabs .tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });
}

const EYE_OPEN_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF_SVG  = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

async function doLogin() {
  const u = document.getElementById('loginUsername').value.trim();
  const p = document.getElementById('loginPassword').value;
  const err = document.getElementById('loginErr');
  err.className = 'alert'; err.textContent = '';
  try {
    const body = new URLSearchParams();
    body.append('username', u); body.append('password', p);
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      let msg = 'Login failed';
      if (data.detail && typeof data.detail === 'string') msg = data.detail;
      else if (res.status === 401) msg = '❌ Incorrect username or password';
      else if (res.status === 422) msg = '⚠ Please fill in username and password';
      showAlert(err, msg, 'error'); return;
    }
    await finishLogin(data.access_token);
  } catch(e) { showAlert(err, 'Cannot reach API — is the server running?', 'error'); }
}

async function doRegister() {
  const u = document.getElementById('regUsername').value.trim();
  const e = document.getElementById('regEmail').value.trim();
  const p = document.getElementById('regPassword').value;
  const err = document.getElementById('registerErr');
  err.className = 'alert'; err.textContent = '';
  try {
    const res = await fetch(`${API}/auth/register`, {
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
      const loginRes = await fetch(`${API}/auth/login`, {
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
let _obFullName = '';

function openOnboarding() {
  const initial = (username || '?')[0].toUpperCase();
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

function closeOnboarding() {
  document.getElementById('onboardingModal').style.display = 'none';
}

function obNextStep() {
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

function obSkipStep() {
  _obFullName = '';
  obNextStep();
}

async function obFinish(skipDob = false) {
  const dob = skipDob ? null : (document.getElementById('obDob').value || null);
  const payload = {};
  if (_obFullName) payload.full_name = _obFullName;
  if (dob) payload.date_of_birth = dob;

  if (Object.keys(payload).length > 0 && token) {
    try {
      await fetch(`${API}/auth/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
    } catch(e) { /* non-fatal, user can set later in settings */ }
  }

  closeOnboarding();
  // Refresh current page data
  if (_settingsData) Object.assign(_settingsData, payload);
  await loadDashboard();
}

// ── GitHub OAuth ──────────────────────────────────────────────────────
let _githubSetupToken = null;
let _githubConnectMode = false; // true = connecting to existing account, false = new login

function startGitHubOAuth(connectMode = false) {
  _githubConnectMode = connectMode;
  // Pop a small window for GitHub OAuth so we can capture the redirect
  const w = 600, h = 700;
  const left = Math.max(0, (screen.width - w) / 2);
  const top  = Math.max(0, (screen.height - h) / 2);
  const popup = window.open(
    `${API}/auth/github`,
    'github-oauth',
    `width=${w},height=${h},left=${left},top=${top},scrollbars=yes`
  );
  // Listen for the callback message from the popup (we'll post a message from the callback page)
  const handler = async (e) => {
    if (!e.data || e.data.type !== 'github-oauth') return;
    window.removeEventListener('message', handler);
    if (popup && !popup.closed) popup.close();
    await handleGitHubOAuthResult(e.data.code);
  };
  window.addEventListener('message', handler);
}

async function handleGitHubOAuthResult(code) {
  const al = document.getElementById('githubSetupErr');
  try {
    if (_githubConnectMode) {
      // Connect GitHub to existing logged-in account
      const res = await fetch(`${API}/auth/github/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      const socialAlert = document.getElementById('sSocialAlert');
      if (!res.ok) {
        if (socialAlert) { socialAlert.className = 'alert error'; socialAlert.textContent = data.detail || 'GitHub connect failed.'; }
        return;
      }
      if (socialAlert) { socialAlert.className = 'alert success'; socialAlert.textContent = 'GitHub connected successfully!'; }
      // Refresh settings data
      if (typeof loadSettings === 'function') loadSettings();
      _githubConnectMode = false;
      return;
    }

    // Login / signup flow
    const res = await fetch(`${API}/auth/github/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const data = await res.json();

    if (!res.ok) {
      // Account conflict or error
      showGitHubSetupForm(null);
      if (al) { al.className = 'alert error'; al.textContent = data.detail || 'GitHub sign-in failed.'; }
      return;
    }

    if (data.requires_setup) {
      // New user — show username picker
      _githubSetupToken = data.setup_token;
      showGitHubSetupForm(data.suggested_username || '', data.name);
    } else {
      // Existing user — log in
      closeAuthModal();
      await finishLogin(data.access_token);
    }
  } catch(e) {
    if (al) { al.className = 'alert error'; al.textContent = 'Network error. Please try again.'; }
  }
}

function showGitHubSetupForm(suggestedUsername, name) {
  // Hide all other forms, show GitHub setup
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('googleSetupForm').style.display = 'none';
  document.getElementById('githubSetupForm').style.display = 'block';
  document.getElementById('googleButtonWrap').style.display = 'none';
  document.getElementById('githubSignInBtn').style.display = 'none';
  document.getElementById('googleDivider').style.display = 'none';
  if (document.getElementById('authTabs')) document.getElementById('authTabs').style.display = 'none';
  if (suggestedUsername !== null) {
    document.getElementById('githubSetupUsername').value = suggestedUsername || '';
    document.getElementById('githubSetupUsername').focus();
  }
}

async function completeGitHubSignup() {
  const uname = document.getElementById('githubSetupUsername').value.trim();
  const al = document.getElementById('githubSetupErr');
  al.className = 'alert'; al.textContent = '';
  if (!uname) { al.className = 'alert error'; al.textContent = 'Please choose a username.'; return; }
  if (!_githubSetupToken) { al.className = 'alert error'; al.textContent = 'Session expired. Please try again.'; return; }
  try {
    const res = await fetch(`${API}/auth/complete-github-signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: uname, setup_token: _githubSetupToken, password: null }),
    });
    const data = await res.json();
    if (!res.ok) {
      al.className = 'alert error'; al.textContent = data.detail || 'Sign up failed.'; return;
    }
    _githubSetupToken = null;
    closeAuthModal();
    await finishLogin(data.access_token);
    openOnboarding();
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}

// Called from settings Social tab
function handleGithubConnect() {
  startGitHubOAuth(true);
}
