// ── Auth Modal & Login/Register ────────────────────────────────────

// ── Auth ───────────────────────────────────────────────────────────
function openAuthModal() { document.getElementById('authModal').classList.add('show'); }
function closeAuthModal() {
  document.getElementById('authModal').classList.remove('show');
  hideGoogleSetupForm();
  pendingGoogleSetupToken = null;
}

function switchAuthTab(tab) {
  document.getElementById('loginForm').style.display        = tab === 'login'    ? 'block' : 'none';
  document.getElementById('registerForm').style.display     = tab === 'register' ? 'block' : 'none';
  document.getElementById('forgotPasswordForm').style.display = 'none'; // always hide on tab switch
  document.querySelectorAll('#authTabs .tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register'));
  });
}

const EYE_OPEN_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

async function doLogin() {
  const u = document.getElementById('loginUsername').value.trim();
  const p = document.getElementById('loginPassword').value;
  const err = document.getElementById('loginErr');
  err.className = 'alert';
  err.textContent = '';

  try {
    // FastAPI's OAuth2PasswordRequestForm expects x-www-form-urlencoded
    const body = new URLSearchParams();
    body.append('username', u);
    body.append('password', p);

    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      let loginMsg = 'Login failed';
      if (data.detail && typeof data.detail === 'string') loginMsg = data.detail;
      else if (res.status === 401) loginMsg = '❌ Incorrect username or password';
      else if (res.status === 422) loginMsg = '⚠ Please fill in username and password';
      showAlert(err, loginMsg, 'error');
      return;
    }

    await finishLogin(data.access_token);

  } catch (e) {
    showAlert(err, 'Cannot reach API — is the server running? (or CORS blocked)', 'error');
  }
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
      let regMsg = 'Registration failed';
      if (data.detail && typeof data.detail === 'string') regMsg = data.detail;
      else if (data.detail && Array.isArray(data.detail)) regMsg = data.detail.map(e => e.msg).join(', ');
      if (regMsg.includes('Username already')) regMsg = '❌ Username already taken';
      if (regMsg.includes('Email already')) regMsg = '❌ Email already registered — try logging in';
      showAlert(err, regMsg, 'error'); return;
    }
    showAlert(err, '✓ Account created! Logging you in…', 'success');
    setTimeout(() => {
      document.getElementById('loginUsername').value = u;
      document.getElementById('loginPassword').value = p;
      switchAuthTab('login');
      doLogin();
    }, 800);
  } catch(e) { showAlert(err, 'Cannot reach API — is the server running?', 'error'); }
}
