// ── Account / Profile Page ──────────────────────────────────────────
// ── My Account ─────────────────────────────────────────────────────
let _accountData = null;

async function loadAccount() {
  if (!token) { openAuthModal(); return; }
  try {
    const res = await fetch(`${API}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();
    _accountData = data;
    // Show display name (full_name) as headline, username below it
    const displayName = data.full_name || data.username;
    document.getElementById('accountDisplayName').textContent = displayName;
    document.getElementById('accountUsername').textContent = '@' + data.username;
    // DOB kept in hidden field for compat
    if (data.date_of_birth) { const el = document.getElementById('accountDob'); if(el) el.value = data.date_of_birth; }
    _renderAccountAvatar(data.profile_picture, data.username);
    document.getElementById('profileAlert').className = 'alert';
    document.getElementById('profileAlert').textContent = '';
    document.getElementById('pwAlert').className = 'alert';
    document.getElementById('pwAlert').textContent = '';
    document.getElementById('pwCurrent').value = '';
    document.getElementById('pwNew').value = '';
    document.getElementById('pwConfirm').value = '';
  } catch(e) {
    console.error('loadAccount error', e);
  }
}

function _renderAccountAvatar(profilePicture, uname) {
  const img = document.getElementById('accountAvatarImg');
  const txt = document.getElementById('accountAvatarText');
  const wrap = document.getElementById('accountAvatarWrapper');
  if (profilePicture) {
    img.src = profilePicture;
    img.style.display = 'block';
    txt.style.display = 'none';
    wrap.style.background = 'transparent';
  } else {
    img.style.display = 'none';
    txt.style.display = '';
    txt.textContent = (uname || '?')[0].toUpperCase();
    wrap.style.background = 'linear-gradient(135deg,var(--accent),#bc8cff)';
  }
}

function previewAvatar(input) {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 200 * 1024) {
    showAlert(document.getElementById('profileAlert'), 'Image must be under 200 KB. Try a smaller photo.', 'error');
    input.value = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = e => {
    _renderAccountAvatar(e.target.result, _accountData?.username);
  };
  reader.readAsDataURL(file);
}

async function saveProfile() {
  if (!token) return;
  const btn = event.target;
  const alertEl = document.getElementById('profileAlert');
  alertEl.className = 'alert'; alertEl.textContent = '';
  btn.disabled = true; btn.textContent = 'Saving…';

  const dob = document.getElementById('accountDob').value || null;
  const img = document.getElementById('accountAvatarImg');
  const profile_picture = img.style.display !== 'none' && img.src && !img.src.endsWith('/') ? img.src : null;

  try {
    const res = await fetch(`${API}/auth/me`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ date_of_birth: dob, profile_picture }),
    });
    const data = await res.json();
    if (!res.ok) { showAlert(alertEl, data.detail || 'Save failed', 'error'); return; }
    _accountData = data;
    // Update top-bar avatar if profile pic changed
    _syncTopBarAvatar(data.profile_picture, data.username);
    showAlert(alertEl, '✓ Profile saved!', 'success');
  } catch(e) {
    showAlert(alertEl, 'Cannot reach API', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Save Profile';
  }
}

function _syncTopBarAvatar(profilePicture, uname) {
  const av = document.getElementById('userAvatar');
  if (!av) return;
  if (profilePicture) {
    av.innerHTML = `<img src="${profilePicture}" style="width:100%;height:100%;border-radius:50%;object-fit:cover" />`;
  } else {
    av.textContent = (uname || '?')[0].toUpperCase();
  }
}

async function changePassword() {
  if (!token) return;
  const btn = event.target;
  const alertEl = document.getElementById('pwAlert');
  alertEl.className = 'alert'; alertEl.textContent = '';
  const current = document.getElementById('pwCurrent').value;
  const newPw   = document.getElementById('pwNew').value;
  const confirm = document.getElementById('pwConfirm').value;

  if (newPw.length < 6) { showAlert(alertEl, 'New password must be at least 6 characters', 'error'); return; }
  if (newPw !== confirm) { showAlert(alertEl, 'Passwords do not match', 'error'); return; }

  btn.disabled = true; btn.textContent = 'Updating…';
  try {
    const res = await fetch(`${API}/auth/change-password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ current_password: current || null, new_password: newPw }),
    });
    const data = await res.json();
    if (!res.ok) { showAlert(alertEl, data.detail || 'Update failed', 'error'); return; }
    document.getElementById('pwCurrent').value = '';
    document.getElementById('pwNew').value = '';
    document.getElementById('pwConfirm').value = '';
    showAlert(alertEl, '✓ Password updated successfully!', 'success');
  } catch(e) {
    showAlert(alertEl, 'Cannot reach API', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Update Password';
  }
}

// ── Forgot Password ─────────────────────────────────────────────────
function showForgotPassword(show = true) {
  document.getElementById('loginForm').style.display = show ? 'none' : 'block';
  document.getElementById('forgotPasswordForm').style.display = show ? 'block' : 'none';
  if (show) {
    document.getElementById('forgotEmail').value = '';
    document.getElementById('forgotErr').className = 'alert';
    document.getElementById('forgotErr').textContent = '';
    document.getElementById('forgotSendBtn').disabled = false;
    document.getElementById('forgotSendBtn').textContent = 'Send Reset Link';
  }
}

async function doForgotPassword() {
  const email = document.getElementById('forgotEmail').value.trim();
  const alertEl = document.getElementById('forgotErr');
  const btn = document.getElementById('forgotSendBtn');
  alertEl.className = 'alert'; alertEl.textContent = '';
  if (!email) { showAlert(alertEl, 'Please enter your email', 'error'); return; }
  btn.disabled = true; btn.textContent = 'Sending…';
  try {
    const res = await fetch(`${API}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) { showAlert(alertEl, data.detail || 'Could not send reset email', 'error'); btn.disabled = false; btn.textContent = 'Send Reset Link'; return; }
    showAlert(alertEl, '✓ Check your inbox — a reset link has been sent to ' + email + '.', 'success');
    btn.textContent = 'Link Sent ✓';
  } catch(e) {
    showAlert(alertEl, 'Cannot reach API', 'error');
    btn.disabled = false; btn.textContent = 'Send Reset Link';
  }
}

// ── Reset Password (landing from the emailed link) ──────────────────
let _resetPwToken = null;

function openResetPasswordModal(resetToken) {
  closeAuthModal();
  _resetPwToken = resetToken;
  document.getElementById('resetPwFormView').style.display = 'block';
  document.getElementById('resetPwSuccessView').style.display = 'none';
  document.getElementById('resetPwErr').className = 'alert';
  document.getElementById('resetPwErr').textContent = '';
  document.getElementById('resetPwNew').value = '';
  document.getElementById('resetPwConfirm').value = '';
  document.getElementById('resetPwSubmitBtn').disabled = false;
  document.getElementById('resetPwSubmitBtn').textContent = 'Reset Password';
  document.getElementById('resetPasswordModal').style.display = 'flex';
}

function closeResetPasswordModal(openLogin) {
  document.getElementById('resetPasswordModal').style.display = 'none';
  _resetPwToken = null;
  history.replaceState({}, '', '#dashboard');
  if (openLogin) openAuthModal();
}

async function submitResetPassword() {
  const alertEl = document.getElementById('resetPwErr');
  const btn = document.getElementById('resetPwSubmitBtn');
  alertEl.className = 'alert'; alertEl.textContent = '';
  const newPw = document.getElementById('resetPwNew').value;
  const confirmPw = document.getElementById('resetPwConfirm').value;

  if (!newPw || newPw.length < 6) { showAlert(alertEl, 'Password must be at least 6 characters', 'error'); return; }
  if (newPw !== confirmPw) { showAlert(alertEl, 'Passwords do not match', 'error'); return; }
  if (!_resetPwToken) { showAlert(alertEl, 'Reset link is invalid or missing a token', 'error'); return; }

  btn.disabled = true; btn.textContent = 'Resetting…';
  try {
    const res = await fetch(`${API}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reset_token: _resetPwToken, new_password: newPw }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAlert(alertEl, data.detail || 'Reset failed — the link may have expired. Request a new one.', 'error');
      btn.disabled = false; btn.textContent = 'Reset Password';
      return;
    }
    document.getElementById('resetPwFormView').style.display = 'none';
    document.getElementById('resetPwSuccessView').style.display = 'block';
  } catch(e) {
    showAlert(alertEl, 'Cannot reach API', 'error');
    btn.disabled = false; btn.textContent = 'Reset Password';
  }
}
