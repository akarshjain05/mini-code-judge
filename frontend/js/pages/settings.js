// ── Settings Page ────────────────────────────────────────────────────

function switchSettingsTab(tab) {
  ['general','social','delete'].forEach(t => {
    document.getElementById('stab-' + t).classList.remove('active');
    document.getElementById('spanel-' + t).style.display = 'none';
  });
  document.getElementById('stab-' + tab).classList.add('active');
  document.getElementById('spanel-' + tab).style.display = '';
}

function openSettings() {
  closeUserMenu();
  goTo('settings');
}

function closeSettings() {
  history.back();
}

async function loadSettings() {
  if (!token) { openAuthModal(); return; }

  switchSettingsTab('general');

  // Reset alerts + password fields
  ['settingsPwAlert','sGeneralAlert','sSocialAlert','sDeleteAlert'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.className = 'alert'; el.textContent = ''; }
  });
  ['settingsPwCurrent','settingsPwNew','settingsPwConfirm','sDeletePassword'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  // Prefill from cached state
  const initial = (username || '?')[0].toUpperCase();
  document.getElementById('settingsAvatar').textContent = initial;
  document.getElementById('settingsUsername').textContent = username || '—';
  document.getElementById('sUsername').value = username || '';

  // Fetch fresh data
  try {
    const res = await fetch(`${API}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) return;
    const d = await res.json();
    _settingsData = d;
    document.getElementById('sFullName').value = d.full_name || '';
    document.getElementById('sEmail').value = d.email || '';
    document.getElementById('settingsEmail').textContent = d.email || '—';
    document.getElementById('dropdownEmail').textContent = d.email || '—';
    document.getElementById('sPhone').value = d.phone_number || '';
    document.getElementById('sDob').value = d.date_of_birth || '';

    const hasGoogle = !!d.has_google;
    document.getElementById('sGoogleStatus').textContent = hasGoogle ? `Connected as ${d.email}` : 'Not connected';
    document.getElementById('sGoogleBtn').textContent = hasGoogle ? 'Connected' : 'Connect';
    document.getElementById('sGoogleBtn').disabled = hasGoogle;

    const noPassword = !d.has_password;
    document.getElementById('sPwNoPasswordNote').style.display = noPassword ? 'block' : 'none';
    document.getElementById('settingsPwCurrent').placeholder = noPassword ? 'Leave blank (no password yet)' : '••••••••';
    document.getElementById('sDeletePwGroup').style.display = noPassword ? 'none' : 'block';
  } catch(e) { console.error('Settings fetch error', e); }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeUserMenu();
});

async function saveGeneralSettings() {
  const al = document.getElementById('sGeneralAlert');
  al.className = 'alert'; al.textContent = '';
  const payload = {
    full_name:    document.getElementById('sFullName').value.trim(),
    phone_number: document.getElementById('sPhone').value.trim(),
    date_of_birth: document.getElementById('sDob').value || null,
  };
  try {
    const res = await fetch(`${API}/auth/me`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      al.className = 'alert error'; al.textContent = data.detail || 'Error saving changes.';
    } else {
      al.className = 'alert success'; al.textContent = 'Changes saved!';
      _settingsData = data;
      // Sync updated DOB back to account page if it's open
      if (document.getElementById('accountDob')) document.getElementById('accountDob').value = data.date_of_birth || '';
    }
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}

async function settingsChangePassword() {
  const current = document.getElementById('settingsPwCurrent').value;
  const newPw   = document.getElementById('settingsPwNew').value;
  const confirm = document.getElementById('settingsPwConfirm').value;
  const al      = document.getElementById('settingsPwAlert');
  al.className = 'alert'; al.textContent = '';
  if (!newPw || !confirm) {
    al.className = 'alert error'; al.textContent = 'Please fill in the new password fields.'; return;
  }
  if (newPw.length < 6) {
    al.className = 'alert error'; al.textContent = 'New password must be at least 6 characters.'; return;
  }
  if (newPw !== confirm) {
    al.className = 'alert error'; al.textContent = 'New passwords do not match.'; return;
  }
  try {
    const res = await fetch(`${API}/auth/change-password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ current_password: current || null, new_password: newPw }),
    });
    const data = await res.json();
    if (!res.ok) {
      al.className = 'alert error'; al.textContent = data.detail || 'Error updating password.';
    } else {
      al.className = 'alert success'; al.textContent = 'Password updated successfully!';
      ['settingsPwCurrent','settingsPwNew','settingsPwConfirm'].forEach(id => {
        document.getElementById(id).value = '';
      });
      // Now they have a password — hide note, show pw field in delete tab
      document.getElementById('sPwNoPasswordNote').style.display = 'none';
      document.getElementById('sDeletePwGroup').style.display = 'block';
      document.getElementById('settingsPwCurrent').placeholder = '••••••••';
    }
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}

function handleGoogleConnect() {
  const al = document.getElementById('sSocialAlert');
  al.className = 'alert'; al.textContent = '';
  // Trigger existing Google one-tap flow
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
  const pw = document.getElementById('sDeletePassword') ? document.getElementById('sDeletePassword').value : null;
  const hasPassword = _settingsData && _settingsData.has_password;
  if (hasPassword && !pw) {
    al.className = 'alert error'; al.textContent = 'Please enter your password to confirm.'; return;
  }
  if (!confirm('Are you absolutely sure? This will permanently delete your account and all data. This cannot be undone.')) return;
  try {
    const res = await fetch(`${API}/auth/me`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ password: pw || null }),
    });
    const data = await res.json();
    if (!res.ok) {
      al.className = 'alert error'; al.textContent = data.detail || 'Error deleting account.';
    } else {
      // Log out and go to dashboard
      token = null; username = null; isAdmin = false;
      localStorage.removeItem('jwt'); localStorage.removeItem('username');
      updateAuthUI(); updateAdminUI();
      goTo('dashboard');
    }
  } catch(e) {
    al.className = 'alert error'; al.textContent = 'Network error. Please try again.';
  }
}
