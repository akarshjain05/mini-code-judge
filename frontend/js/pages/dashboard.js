// ── Dashboard ───────────────────────────────────────────────────────
async function loadDashboard() {
  loadProblems();
  if (token) loadHistory();
  const el = document.getElementById('dashRecentList');
  if (!token) { el.innerHTML = '<p style="color:var(--muted);font-size:13px">Login to see your recent submissions.</p>'; return; }
  try {
    const res = await fetch(`${API}/submissions?limit=5`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (res.status === 401) {
      // Token expired — clear and show logged-out state
      token = null; username = null; isAdmin = false;
      localStorage.removeItem('jwt'); localStorage.removeItem('username');
      updateAuthUI(); updateAdminUI();
      el.innerHTML = '<p style="color:var(--muted);font-size:13px">Session expired. Please <a href="#" onclick="openAuthModal()" style="color:var(--accent)">log in again</a>.</p>';
      return;
    }
    const subs = await res.json();
    if (!subs.length) { el.innerHTML = '<p style="color:var(--muted);font-size:13px">No submissions yet. <a href="#" onclick="goTo(\'problems\')" style="color:var(--accent)">Try a problem →</a></p>'; return; }
    el.innerHTML = subs.map(s => `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid rgba(48,54,61,0.5)">
        <span class="badge ${verdictClass(s.verdict || s.status)}">${formatVerdict(s.verdict || s.status)}</span>
        <span style="font-size:13px">Problem #${s.problem_id}</span>
        <span style="font-family:var(--mono);font-size:11px;color:var(--muted)">${s.language}</span>
        <span style="font-size:12px;color:var(--muted);margin-left:auto">${timeAgo(s.created_at)}</span>
      </div>`).join('');
  } catch(e) {}
}
