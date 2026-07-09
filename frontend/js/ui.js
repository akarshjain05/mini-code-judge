// ── UI Utilities ─────────────────────────────────────────────────────

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  const showing = input.type === 'text';
  input.type = showing ? 'password' : 'text';
  btn.innerHTML = showing ? EYE_OPEN_SVG : EYE_OFF_SVG;
  btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
}

function handleAuthNav() {
  if (token) {
    // Invalidate token server-side (adds to Redis blacklist)
    const _t = token;
    fetch(`${API}/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${_t}` },
    }).catch(() => {}); // fire-and-forget — clear locally regardless
    token = null; username = null; isAdmin = false;
    localStorage.removeItem('username');
    localStorage.removeItem('token');
    updateAuthUI(); updateAdminUI();
    goTo('dashboard');
  } else {
    openAuthModal();
  }
}

function updateAuthUI() {
  const loggedIn = !!token;
  document.getElementById('userPillWrap').style.display = loggedIn ? 'block' : 'none';
  document.getElementById('topAuthBtn').style.display = loggedIn ? 'none' : 'inline-flex';
  if (loggedIn && username) {
    const initial = username[0].toUpperCase();
    document.getElementById('userAvatar').textContent = initial;
    document.getElementById('dropdownAvatar').textContent = initial;
    document.getElementById('dropdownName').textContent = username;
    document.getElementById('dropdownUsername').textContent = '@' + username;
    document.getElementById('settingsAvatar').textContent = initial;
    document.getElementById('settingsUsername').textContent = username;
  }
}

async function fetchCurrentUser() {
  if (!token) { isAdmin = false; updateAdminUI(); return; }
  try {
    const res = await fetch(`${API}/auth/me`, { headers: {} });
    if (res.status === 401) {
      // Token expired or invalid — clear it and show login button
      token = null; username = null; isAdmin = false;
      localStorage.removeItem('username');
      localStorage.removeItem('token');
      updateAuthUI(); updateAdminUI();
      return;
    }
    if (!res.ok) { isAdmin = false; updateAdminUI(); return; }
    const data = await res.json();
    isAdmin = !!data.is_admin;
    username = data.username;
    localStorage.setItem('username', username);
    // Populate email in dropdown and settings
    if (data.email) {
      document.getElementById('dropdownEmail').textContent = data.email;
      document.getElementById('settingsEmail').textContent = data.email;
    }
    // Sync display name in dropdown
    const displayName = data.full_name || data.username;
    document.getElementById('dropdownName').textContent = displayName;
    document.getElementById('dropdownUsername').textContent = '@' + data.username;
    document.getElementById('userAvatar').textContent = displayName[0].toUpperCase();
    document.getElementById('dropdownAvatar').textContent = displayName[0].toUpperCase();
  } catch(e) { isAdmin = false; }
  updateAdminUI();
}

function updateAdminUI() {
  const _u = username || localStorage.getItem('username') || '';
  // Treat as admin if the API says so OR if it's the known admin username
  const effectiveAdmin = isAdmin || _u === 'akarsh';
  const display = effectiveAdmin ? 'flex' : 'none';
  document.getElementById('navAddProblem').style.display = display;
  document.getElementById('settingsSectionLabel').style.display = effectiveAdmin ? 'block' : 'none';
  document.getElementById('adminBadge').style.display = effectiveAdmin ? 'inline-block' : 'none';
  const adminNav = document.getElementById('navAdmin');
  if (adminNav) adminNav.style.display = display;
  const createBtn = document.getElementById('createContestBtn');
  if (createBtn) createBtn.style.display = effectiveAdmin ? 'block' : 'none';
}

/* ── User dropdown ────────────────────────────────────────────── */
function toggleUserMenu(e) {
  e.stopPropagation();
  const d = document.getElementById('userDropdown');
  const open = d.style.display === 'block';
  d.style.display = open ? 'none' : 'block';
  if (!open) {
    // close when clicking anywhere else
    setTimeout(() => document.addEventListener('click', closeUserMenuHandler, { once: true }), 0);
  }
}
function closeUserMenuHandler() {
  document.getElementById('userDropdown').style.display = 'none';
}
function closeUserMenu() {
  document.getElementById('userDropdown').style.display = 'none';
}

/* ── Settings modal ───────────────────────────────────────────── */
/* ── Settings page ────────────────────────────────────────────── */

// ── Utils ──────────────────────────────────────────────────────────
function showAlert(el, msg, type) {
  el.className = `alert alert-${type} show`;
  el.textContent = msg;
}

function showToast(msg, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<div>${icon}</div><div>${msg}</div>`;
  
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 250);
  }, 3000);
}

function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h/24)}d ago`;
}

// Close modal on backdrop click
document.getElementById('authModal').addEventListener('click', function(e) {
  if (e.target === this) closeAuthModal();
});

/**
 * Fully resets the problem-solving screen (code editor, verdict box, judge
 * log, and AI review button/panel) back to its pristine state. Called
 * whenever a problem is opened, so nothing from a previous problem or
 * previous submission (including a stuck "Analyzing…" button) can leak
 * into the freshly opened screen.
 */
function resetSubmitScreen() {
  // Stop any in-flight polling left over from a previous problem/submission.
  if (typeof pollInterval !== 'undefined' && pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  if (typeof runPollInterval !== 'undefined' && runPollInterval) { clearInterval(runPollInterval); runPollInterval = null; }
  window._lastSubId = null;
  window._pollStartedAt = null;
  window._pollFailCount = 0;

  // Code editor back to its default (empty, C++ placeholder).
  const codeInput = document.getElementById('codeInput');
  if (codeInput) codeInput.value = '';
  const langSelect = document.getElementById('langSelect');
  if (langSelect) langSelect.value = 'cpp';
  updateCodePlaceholder();

  // Verdict box.
  const vbox = document.getElementById('verdictBox');
  if (vbox) vbox.classList.remove('show');
  const vtitle = document.getElementById('verdictTitle');
  if (vtitle) { vtitle.textContent = '—'; vtitle.className = 'verdict-title'; }
  const vsub = document.getElementById('verdictSub');
  if (vsub) vsub.textContent = '';
  const vmeta = document.getElementById('verdictMeta');
  if (vmeta) vmeta.textContent = '';
  const verr = document.getElementById('verdictError');
  if (verr) { verr.textContent = ''; verr.style.display = 'none'; }

  // Judge log.
  const log = document.getElementById('submitLog');
  if (log) log.style.display = 'none';
  const logText = document.getElementById('submitLogText');
  if (logText) logText.textContent = '';

  // AI review button + panel — back to their untouched, never-clicked state.
  const aiBtn = document.getElementById('aiReviewBtn');
  if (aiBtn) {
    aiBtn.style.display = 'none';
    aiBtn.disabled = false;
    aiBtn.textContent = '🤖 Get AI Code Review';
    delete aiBtn.dataset.submissionId;
    delete aiBtn.dataset.verdict;
  }
  const aiPanel = document.getElementById('aiReviewPanel');
  if (aiPanel) aiPanel.style.display = 'none';
  const aiContent = document.getElementById('aiReviewContent');
  if (aiContent) {
    aiContent.innerHTML = '<div id="aiReviewLoading" style="display:flex;align-items:center;gap:10px;color:var(--muted)"><span class="spinner"></span> Analyzing your code…</div>';
  }

  // Sample tests card (loadSampleTestCases will re-show it if applicable).
  const sampleCard = document.getElementById('sampleTestsCard');
  if (sampleCard) sampleCard.style.display = 'none';
}

function updateCodePlaceholder() {
  const lang = document.getElementById('langSelect').value;
  const ta = document.getElementById('codeInput');
  const ph = {
    cpp: '#include<bits/stdc++.h>\nusing namespace std;\nint main(){\n    \n    return 0;\n}',
    c: '#include <stdio.h>\nint main(){\n    \n    return 0;\n}',
    java: 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}',
    python: '# Python solution\nimport sys\ninput = sys.stdin.readline\n\n'
  };
  ta.placeholder = ph[lang] || '';
  ta.value = ph[lang] || '';

async function loadSampleTestCases(problemId, retriesLeft = 2) {
  const card = document.getElementById('sampleTestsCard');
  const list = document.getElementById('sampleTestsList');
  try {
    const res = await fetch(`${API}/problems/${problemId}/sample-tests`);
    if (!res.ok) { card.style.display = 'none'; return; }
    const tests = await res.json();
    if (!tests || !tests.length) { card.style.display = 'none'; return; }
    card.style.display = 'block';
    list.innerHTML = tests.map((t, i) => `
      <div style="margin-bottom:10px;border:1px solid var(--border);border-radius:6px;overflow:hidden">
        <div style="padding:5px 10px;background:var(--surface2);font-size:11px;color:var(--muted)">Sample ${i+1}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr">
          <div style="padding:8px 10px;border-right:1px solid var(--border)">
            <div style="font-size:10px;color:var(--muted);margin-bottom:3px">INPUT</div>
            <pre style="font-size:12px;font-family:var(--mono);margin:0;white-space:pre-wrap">${t.stdin || '(none)'}</pre>
          </div>
          <div style="padding:8px 10px">
            <div style="font-size:10px;color:var(--muted);margin-bottom:3px">EXPECTED OUTPUT</div>
            <pre style="font-size:12px;font-family:var(--mono);color:var(--accent2);margin:0;white-space:pre-wrap">${t.expected}</pre>
          </div>
        </div>
      </div>`).join('');
  } catch(e) {
    // Render free-tier cold start can make the very first request fail —
    // retry a couple of times with backoff before giving up silently.
    if (retriesLeft > 0) {
      await new Promise(r => setTimeout(r, 2500));
      return loadSampleTestCases(problemId, retriesLeft - 1);
    }
    card.style.display = 'none';
  }
}

let runPollInterval = null;

async function runCode() {
  if (!token) { openAuthModal(); return; }
  if (!currentProblem) { alert('Select a problem first'); return; }
  const code = document.getElementById('codeInput').value.trim();
  const lang = document.getElementById('langSelect').value;
  if (!code) { alert('Please write some code first'); return; }

  const vbox = document.getElementById('verdictBox');
  const vtitle = document.getElementById('verdictTitle');
  const vsub = document.getElementById('verdictSub');
  const vmeta = document.getElementById('verdictMeta');
  const verr = document.getElementById('verdictError');

  // Clear any previous judging log
  document.getElementById('submitLog').style.display = 'none';
  document.getElementById('submitLogText').textContent = '';
  vbox.classList.add('show');
  vtitle.className = 'verdict-title verdict-pending';
  vtitle.innerHTML = '<span class="spinner"></span> Testing sample cases…';
  vsub.textContent = '';
  vmeta.textContent = ''; verr.style.display = 'none';
  const aiBtn = document.getElementById('aiReviewBtn');
  if (aiBtn) {
    aiBtn.style.display = 'none';
    aiBtn.disabled = false;
    aiBtn.textContent = '🤖 Get AI Code Review';
    delete aiBtn.dataset.submissionId;
    delete aiBtn.dataset.verdict;
  }
  const aiPanel = document.getElementById('aiReviewPanel');
  if (aiPanel) aiPanel.style.display = 'none';

  try {
    const res = await apiFetch(`${API}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem_id: currentProblem.id, language: lang, code, sample_only: true }),
    });
    let sub;
    try {
      sub = await res.json();
    } catch(err) {
      sub = { detail: `Status ${res.status}: Invalid JSON response` };
    }
    if (!res.ok) {
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = '✗ Error';
      vsub.textContent = sub.detail || 'Run failed';
      return;
    }
    if (!sub.id) {
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = '✗ Error';
      vsub.textContent = 'Invalid server response (missing submission id)';
      return;
    }

    if (runPollInterval) clearInterval(runPollInterval);
    window._runPollStartedAt = Date.now();
    window._runPollFailCount = 0;
    runPollInterval = setInterval(() => pollSampleRun(sub.id, vtitle, vsub, vmeta, verr), 1200);
  } catch(e) {
    vtitle.className = 'verdict-title verdict-wrong_answer';
    vtitle.textContent = '⚠ Cannot reach API';
    vsub.textContent = 'Server may be waking up — try again in a moment.';
  }
}

async function pollSampleRun(id, vtitle, vsub, vmeta, verr) {
  if (window._runPollStartedAt && Date.now() - window._runPollStartedAt > 180000) {
    clearInterval(runPollInterval);
    vtitle.className = 'verdict-title verdict-wrong_answer';
    vtitle.textContent = '⏱ Run timed out';
    vsub.textContent = 'The server took too long — try again.';
    return;
  }
  try {
    const res = await fetch(`${API}/submissions/${id}`, { headers: {} });
    if (!res.ok) {
      window._runPollFailCount = (window._runPollFailCount || 0) + 1;
      if (window._runPollFailCount >= 5) {
        clearInterval(runPollInterval);
        vtitle.className = 'verdict-title verdict-wrong_answer';
        vtitle.textContent = '⚠ Cannot reach API';
        vsub.textContent = `Poll failed (HTTP ${res.status}) — refresh and try again.`;
      }
      return;
    }
    window._runPollFailCount = 0;
    const sub = await res.json();
    if (sub.status === 'pending' || sub.status === 'running') return;
    clearInterval(runPollInterval);

    if (sub.verdict === 'accepted') {
      vtitle.className = 'verdict-title verdict-accepted';
      vtitle.textContent = '✓ All sample tests passed!';
      vsub.textContent = 'Sample test cases passed · not submitted';
      vmeta.innerHTML = sub.runtime_ms ? `<span>⚡ ${sub.runtime_ms.toFixed(1)} ms</span>` : '';
    } else if (sub.verdict === 'compile_error') {
      vtitle.className = 'verdict-title verdict-compile_error';
      vtitle.textContent = '✗ Compile Error';
      vsub.textContent = '';
      if (sub.error_output && sub.error_output !== 'SAMPLE_ONLY') { verr.textContent = sub.error_output; verr.style.display = 'block'; }
    } else {
      const labels = { wrong_answer: '✗ Wrong Answer', time_limit_exceeded: '⏱ Time Limit Exceeded', runtime_error: '✗ Runtime Error' };
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = labels[sub.verdict] || '✗ ' + formatVerdict(sub.verdict || sub.status);
      vsub.textContent = 'Failed on a sample test case · not submitted';
      if (sub.error_output && sub.error_output !== 'SAMPLE_ONLY') { verr.textContent = sub.error_output; verr.style.display = 'block'; }
      vmeta.innerHTML = sub.runtime_ms ? `<span>⚡ ${sub.runtime_ms.toFixed(1)} ms</span>` : '';
    }
  } catch(e) {
    window._runPollFailCount = (window._runPollFailCount || 0) + 1;
    if (window._runPollFailCount >= 5) {
      clearInterval(runPollInterval);
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = '⚠ Cannot reach API';
      vsub.textContent = 'Lost connection while waiting for result — try again.';
    }
  }
}

/* ── Appearance / Theme ─────────────────────────────────────────── */
function _applyTheme(theme) {
  const root = document.documentElement;
  root.classList.remove('light');
  if (theme === 'light') {
    root.classList.add('light');
  } else if (theme === 'system') {
    if (window.matchMedia('(prefers-color-scheme: light)').matches) root.classList.add('light');
  }
  // Update checkmarks
  ['system','dark','light'].forEach(t => {
    const el = document.getElementById('theme-' + t);
    if (el) el.classList.toggle('active', t === theme);
  });
}

function setTheme(theme) {
  localStorage.setItem('theme', theme);
  _applyTheme(theme);
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'system';
  _applyTheme(saved);
  // Listen for OS-level changes when in system mode
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
    if ((localStorage.getItem('theme') || 'system') === 'system') _applyTheme('system');
  });
}

function toggleAppearanceSubmenu(e) {
  e.stopPropagation();
  const sub = document.getElementById('appearanceSubmenu');
  sub.style.display = sub.style.display === 'block' ? 'none' : 'block';
}

/* ── Filter Popovers ── */
function toggleDropdownMenu(popoverId, btnElement, e) {
  if (e) e.stopPropagation();
  const popover = document.getElementById(popoverId);
  const isOpen = popover.classList.contains('show');
  
  // Close all open popovers first
  document.querySelectorAll('.filter-popover.show').forEach(p => p.classList.remove('show'));
  document.querySelectorAll('.filter-btn.active').forEach(b => b.classList.remove('active'));
  
  if (!isOpen) {
    popover.classList.add('show');
    btnElement.classList.add('active');
  }
}

// Close popovers when clicking outside
document.addEventListener('click', function(e) {
  if (!e.target.closest('.filter-popover-wrap')) {
    document.querySelectorAll('.filter-popover.show').forEach(p => p.classList.remove('show'));
    document.querySelectorAll('.filter-btn.active').forEach(b => b.classList.remove('active'));
  }
});
