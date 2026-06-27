// ── Settings Page ────────────────────────────────────────────────────

function switchSettingsTab(tab) {
  ['general','social','appearance','delete'].forEach(t => {
    const tabEl = document.getElementById('stab-' + t);
    const panEl = document.getElementById('spanel-' + t);
    if (tabEl) tabEl.classList.remove('active');
    if (panEl) panEl.style.display = 'none';
  });
  const activeTab = document.getElementById('stab-' + tab);
  const activePanel = document.getElementById('spanel-' + tab);
  if (activeTab) activeTab.classList.add('active');
  if (activePanel) activePanel.style.display = '';
  // Sync appearance active state when switching to that tab
  if (tab === 'appearance') _syncAppearancePanel();
}

function openSettings() { closeUserMenu(); goTo('settings'); }
function closeSettings() { history.back(); }

async function loadSettings() {
  if (!token) { openAuthModal(); return; }
  switchSettingsTab('general');

  ['sGeneralAlert','sSocialAlert','sDeleteAlert'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.className = 'alert'; el.textContent = ''; }
  });

  const initial = (username || '?')[0].toUpperCase();
  document.getElementById('settingsAvatar').textContent = initial;
  document.getElementById('settingsUsername').textContent = username || '—';
  document.getElementById('sRowUsername').textContent = username || '—';

  try {
    const res = await fetch(`${API}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) return;
    const d = await res.json();
    _settingsData = d;
    _syncSettingsRows(d);
  } catch(e) { console.error('Settings fetch error', e); }
}

function _syncSettingsRows(d) {
  const email = d.email || '—';
  document.getElementById('settingsEmail').textContent = email;
  document.getElementById('dropdownEmail').textContent = email;
  document.getElementById('sRowEmail').textContent = email;
  document.getElementById('sRowEmail').style.color = 'var(--text)';

  const fn = d.full_name || '';
  const fnEl = document.getElementById('sRowFullName');
  fnEl.textContent = fn || 'Not set';
  fnEl.style.color = fn ? 'var(--text)' : 'var(--muted)';

  const ph = d.phone_number || '';
  const phEl = document.getElementById('sRowPhone');
  phEl.textContent = ph || 'Not set';
  phEl.style.color = ph ? 'var(--text)' : 'var(--muted)';

  const dob = d.date_of_birth || '';
  const dobEl = document.getElementById('sRowDob');
  dobEl.textContent = dob ? _formatDob(dob) : 'Not set';
  dobEl.style.color = dob ? 'var(--text)' : 'var(--muted)';

  const hasPw = !!d.has_password;
  const pwEl = document.getElementById('sRowPassword');
  pwEl.textContent = hasPw ? '••••••••' : 'Not set';
  pwEl.style.color = hasPw ? 'var(--muted)' : 'var(--muted)';

  // Google social
  const hasGoogle = !!d.has_google;
  document.getElementById('sGoogleStatus').textContent = hasGoogle ? `Connected as ${d.email}` : 'Not connected';
  document.getElementById('sGoogleBtn').textContent = hasGoogle ? 'Connected' : 'Connect';
  document.getElementById('sGoogleBtn').disabled = hasGoogle;

  const hasGithub = !!d.has_github;
  document.getElementById('sGithubStatus').textContent = hasGithub ? 'Connected' : 'Not connected';
  document.getElementById('sGithubBtn').textContent = hasGithub ? 'Connected' : 'Connect';
  document.getElementById('sGithubBtn').disabled = hasGithub;

  // Delete tab password field
  const delPwGrp = document.getElementById('sDeletePwGroup');
  if (delPwGrp) delPwGrp.style.display = d.has_password ? 'block' : 'none';
}

function _formatDob(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  if (!y || !m || !d) return iso;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[parseInt(m,10)-1]} ${parseInt(d,10)}, ${y}`;
}

// ── Field edit popup ─────────────────────────────────────────────────
let _currentField = null;

const FIELD_CONFIG = {
  fullname: {
    title: 'Full Name',
    body: () => `
      <div style="font-size:12px;color:var(--muted);margin-bottom:14px">Enter your real name as you'd like it displayed.</div>
      <div class="form-group" style="margin:0">
        <label>Full Name</label>
        <input type="text" id="sfe-fullname" placeholder="e.g. Akarsh Jain" maxlength="100"
          value="${(_settingsData && _settingsData.full_name) || ''}"
          style="font-size:14px" />
      </div>`,
    save: async () => {
      const val = document.getElementById('sfe-fullname').value.trim();
      return await _patchMe({ full_name: val || null });
    },
    onSuccess: (d) => {
      const el = document.getElementById('sRowFullName');
      el.textContent = d.full_name || 'Not set';
      el.style.color = d.full_name ? 'var(--text)' : 'var(--muted)';
    }
  },
  phone: {
    title: 'Phone Number',
    body: () => `
      <div style="font-size:12px;color:var(--muted);margin-bottom:14px">Include country code, e.g. +91 98765 43210.</div>
      <div class="form-group" style="margin:0">
        <label>Phone Number</label>
        <input type="tel" id="sfe-phone" placeholder="+91 98765 43210" maxlength="20"
          value="${(_settingsData && _settingsData.phone_number) || ''}"
          style="font-size:14px" />
      </div>`,
    save: async () => {
      const val = document.getElementById('sfe-phone').value.trim();
      return await _patchMe({ phone_number: val || null });
    },
    onSuccess: (d) => {
      const el = document.getElementById('sRowPhone');
      el.textContent = d.phone_number || 'Not set';
      el.style.color = d.phone_number ? 'var(--text)' : 'var(--muted)';
    }
  },
  dob: {
    title: 'Date of Birth',
    body: () => `
      <div style="font-size:12px;color:var(--muted);margin-bottom:14px">Used only for your profile. Not shown publicly.</div>
      <div class="form-group" style="margin:0">
        <label>Date of Birth</label>
        <input type="date" id="sfe-dob"
          value="${(_settingsData && _settingsData.date_of_birth) || ''}"
          max="${new Date().toISOString().split('T')[0]}"
          style="color:var(--text);background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px 14px;font-size:14px;width:100%;outline:none" />
      </div>`,
    save: async () => {
      const val = document.getElementById('sfe-dob').value;
      return await _patchMe({ date_of_birth: val || null });
    },
    onSuccess: (d) => {
      const el = document.getElementById('sRowDob');
      el.textContent = d.date_of_birth ? _formatDob(d.date_of_birth) : 'Not set';
      el.style.color = d.date_of_birth ? 'var(--text)' : 'var(--muted)';
    }
  },
  password: {
    title: 'Change Password',
    body: () => {
      const noPassword = _settingsData && !_settingsData.has_password;
      return `
      ${noPassword ? `<div style="font-size:12px;color:var(--accent);background:rgba(88,166,255,0.08);border:1px solid rgba(88,166,255,0.2);border-radius:8px;padding:10px 14px;margin-bottom:16px">
        You signed in with Google. Set a password below to also enable username/password login.
      </div>` : ''}
      <div class="form-group">
        <label>Current Password</label>
        <div style="position:relative">
          <input type="password" id="sfe-pwcur" placeholder="${noPassword ? 'Leave blank (Google user)' : '••••••••'}" style="padding-right:42px;font-size:14px" />
          <button type="button" onclick="togglePasswordVisibility('sfe-pwcur',this)" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:var(--muted);padding:4px;display:flex">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>
      <div class="form-group">
        <label>New Password</label>
        <div style="position:relative">
          <input type="password" id="sfe-pwnew" placeholder="min 8 chars, 1 letter, 1 number" style="padding-right:42px;font-size:14px" />
          <button type="button" onclick="togglePasswordVisibility('sfe-pwnew',this)" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:var(--muted);padding:4px;display:flex">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>
      <div class="form-group" style="margin:0">
        <label>Confirm New Password</label>
        <div style="position:relative">
          <input type="password" id="sfe-pwconfirm" placeholder="repeat new password" style="padding-right:42px;font-size:14px" />
          <button type="button" onclick="togglePasswordVisibility('sfe-pwconfirm',this)" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:var(--muted);padding:4px;display:flex">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>`;
    },
    save: async () => {
      const cur  = document.getElementById('sfe-pwcur').value;
      const nw   = document.getElementById('sfe-pwnew').value;
      const conf = document.getElementById('sfe-pwconfirm').value;
      const al   = document.getElementById('sFieldAlert');
      if (!nw) { al.className='alert error'; al.textContent='Enter a new password.'; return null; }
      if (nw.length < 8) { al.className='alert error'; al.textContent='Password must be at least 8 characters with 1 letter and 1 number.'; return null; }
      if (nw !== conf) { al.className='alert error'; al.textContent='Passwords do not match.'; return null; }
      const res = await fetch(`${API}/auth/change-password`, {
        method: 'PUT',
        headers: { 'Content-Type':'application/json', 'Authorization':`Bearer ${token}` },
        body: JSON.stringify({ current_password: cur || null, new_password: nw }),
      });
      const data = await res.json();
      if (!res.ok) { al.className='alert error'; al.textContent = data.detail || 'Error updating password.'; return null; }
      if (_settingsData) _settingsData.has_password = true;
      return data; // signal success even though it's not a UserOut
    },
    onSuccess: () => {
      document.getElementById('sRowPassword').textContent = '••••••••';
      const delPwGrp = document.getElementById('sDeletePwGroup');
      if (delPwGrp) delPwGrp.style.display = 'block';
    }
  },
};

function openFieldEdit(field) {
  const cfg = FIELD_CONFIG[field];
  if (!cfg) return;
  _currentField = field;
  document.getElementById('sFieldTitle').textContent = cfg.title;
  document.getElementById('sFieldBody').innerHTML = cfg.body();
  document.getElementById('sFieldAlert').className = 'alert';
  document.getElementById('sFieldAlert').textContent = '';
  document.getElementById('sFieldOverlay').style.display = 'flex';
  // Focus first input
  setTimeout(() => {
    const inp = document.querySelector('#sFieldBody input');
    if (inp) inp.focus();
  }, 80);
}

function closeFieldEdit() {
  document.getElementById('sFieldOverlay').style.display = 'none';
  _currentField = null;
}

async function saveFieldEdit() {
  const cfg = FIELD_CONFIG[_currentField];
  if (!cfg) return;
  const btn = document.getElementById('sFieldSaveBtn');
  btn.disabled = true; btn.textContent = 'Saving…';
  const al = document.getElementById('sFieldAlert');
  al.className = 'alert'; al.textContent = '';
  try {
    const result = await cfg.save();
    if (result !== null) {
      if (_settingsData && result && result.username) {
        _settingsData = result;
        _syncSettingsRows(result);
      }
      if (cfg.onSuccess) cfg.onSuccess(result || _settingsData);
      closeFieldEdit();
    }
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
  btn.disabled = false; btn.textContent = 'Save';
}

async function _patchMe(payload) {
  const res = await fetch(`${API}/auth/me`, {
    method: 'PUT',
    headers: { 'Content-Type':'application/json', 'Authorization':`Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    const al = document.getElementById('sFieldAlert');
    al.className = 'alert error'; al.textContent = data.detail || 'Error saving.';
    return null;
  }
  if (_settingsData) Object.assign(_settingsData, data);
  return data;
}

// Keyboard: Enter submits popup, Escape closes
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeUserMenu();
    if (document.getElementById('sFieldOverlay').style.display === 'flex') closeFieldEdit();
  }
  if (e.key === 'Enter' && document.getElementById('sFieldOverlay').style.display === 'flex') {
    const active = document.activeElement;
    if (active && active.tagName === 'INPUT') saveFieldEdit();
  }
});

// Stubs kept for backward compat (no longer used as open inputs)
function saveGeneralSettings() {}
function settingsChangePassword() {}

function handleGoogleConnect() {
  const al = document.getElementById('sSocialAlert');
  al.className = 'alert'; al.textContent = '';
  if (window.google && google.accounts && google.accounts.id) {
    google.accounts.id.prompt();
    al.className = 'alert'; al.textContent = 'Check for the Google sign-in prompt on screen.';
  } else {
    al.className = 'alert error'; al.textContent = 'Google sign-in is not available. Try refreshing the page.';
  }
}

async function confirmDeleteAccount() {
  const al = document.getElementById('sDeleteAlert');
  al.className = 'alert'; al.textContent = '';
  const pwEl = document.getElementById('sDeletePassword');
  const pw = pwEl ? pwEl.value : null;
  const hasPassword = _settingsData && _settingsData.has_password;
  if (hasPassword && !pw) {
    al.className = 'alert error'; al.textContent = 'Please enter your password to confirm.'; return;
  }
  if (!confirm('Are you absolutely sure? This will permanently delete your account and all data. This cannot be undone.')) return;
  try {
    const res = await fetch(`${API}/auth/me`, {
      method: 'DELETE',
      headers: { 'Content-Type':'application/json', 'Authorization':`Bearer ${token}` },
      body: JSON.stringify({ password: pw || null }),
    });
    const data = await res.json();
    if (!res.ok) {
      al.className = 'alert error'; al.textContent = data.detail || 'Error deleting account.';
    } else {
      token = null; username = null; isAdmin = false;
      localStorage.removeItem('jwt'); localStorage.removeItem('username');
      updateAuthUI(); updateAdminUI();
      goTo('dashboard');
    }
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}

// ── Appearance panel sync ─────────────────────────────────────────
function _syncAppearancePanel() {
  const saved = localStorage.getItem('theme') || 'system';
  ['system','dark','light'].forEach(t => {
    const el = document.getElementById('choice-' + t);
    if (el) el.classList.toggle('active', t === saved);
  });
}

// Override setTheme to also update the settings panel when it's open
const _origSetTheme = window.setTheme || setTheme;
window.setTheme = function(theme) {
  localStorage.setItem('theme', theme);
  if (typeof _applyTheme === 'function') _applyTheme(theme);
  _syncAppearancePanel();
};