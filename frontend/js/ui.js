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
    token = null; username = null; isAdmin = false;
    localStorage.removeItem('jwt'); localStorage.removeItem('username');
    updateAuthUI(); updateAdminUI();
    // Leave whatever page was active (it may show another user's data, or
    // require login) and land on the public Dashboard view.
    goTo('dashboard');
  } else {
    openAuthModal();
  }
}

function updateAuthUI() {
  const loggedIn = !!token;
  document.getElementById('userPillWrap').style.display = loggedIn ? 'block' : 'none';
  document.getElementById('topAuthBtn').style.display = loggedIn ? 'none' : 'inline-flex';
  if (loggedIn) {
    const initial = (username || '?')[0].toUpperCase();
    document.getElementById('userAvatar').textContent = initial;
    document.getElementById('dropdownAvatar').textContent = initial;
    document.getElementById('dropdownName').textContent = username || '—';
    document.getElementById('settingsAvatar').textContent = initial;
    document.getElementById('settingsUsername').textContent = username || '—';
  }
}

async function fetchCurrentUser() {
  if (!token) { isAdmin = false; updateAdminUI(); return; }
  try {
    const res = await fetch(`${API}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (res.status === 401) {
      // Token expired or invalid — clear it and show login button
      token = null; username = null; isAdmin = false;
      localStorage.removeItem('jwt'); localStorage.removeItem('username');
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
    document.getElementById('userAvatar').textContent = displayName[0].toUpperCase();
    document.getElementById('dropdownAvatar').textContent = displayName[0].toUpperCase();
  } catch(e) { isAdmin = false; }
  updateAdminUI();
}

function updateAdminUI() {
  const display = isAdmin ? 'flex' : 'none';
  document.getElementById('navAddProblem').style.display = display;
  document.getElementById('settingsSectionLabel').style.display = isAdmin ? 'block' : 'none';
  document.getElementById('adminBadge').style.display = isAdmin ? 'inline-block' : 'none';
  const _u = username || localStorage.getItem('username') || '';
  const adminNav = document.getElementById('navAdmin');
  if (adminNav) adminNav.style.display = _u === 'akarsh' ? 'flex' : 'none';
  const createBtn = document.getElementById('createContestBtn');
  if (createBtn) createBtn.style.display = _u === 'akarsh' ? 'block' : 'none';
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
}

async function loadSampleTestCases(problemId) {
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
  } catch(e) { card.style.display = 'none'; }
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
  if (aiBtn) aiBtn.style.display = 'none';
  const aiPanel = document.getElementById('aiReviewPanel');
  if (aiPanel) aiPanel.style.display = 'none';

  try {
    const res = await fetch(`${API}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ problem_id: currentProblem.id, language: lang, code, sample_only: true }),
    });
    const sub = await res.json();
    if (!res.ok) {
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = '✗ Error';
      vsub.textContent = sub.detail || 'Run failed';
      return;
    }

    if (runPollInterval) clearInterval(runPollInterval);
    runPollInterval = setInterval(() => pollSampleRun(sub.id, vtitle, vsub, vmeta, verr), 1200);
  } catch(e) {
    vtitle.className = 'verdict-title verdict-wrong_answer';
    vtitle.textContent = '⚠ Cannot reach API';
    vsub.textContent = '';
  }
}

async function pollSampleRun(id, vtitle, vsub, vmeta, verr) {
  try {
    const res = await fetch(`${API}/submissions/${id}`, { headers: { 'Authorization': `Bearer ${token}` } });
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
    clearInterval(runPollInterval);
    vtitle.className = 'verdict-title verdict-wrong_answer';
    vtitle.textContent = '⚠ Cannot reach API';
    vsub.textContent = '';
  }
}