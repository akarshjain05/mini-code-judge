// ── Dashboard ───────────────────────────────────────────────────────
async function loadDashboard() {
  loadProblems();
  if (token) loadHistory();
  const el = document.getElementById('dashRecentList');
  if (!token) { el.innerHTML = '<p style="color:var(--muted);font-size:13px">Login to see your recent submissions.</p>'; return; }
  try {
    const res = await fetch(`${API}/submissions?limit=5`, { headers: {} });
    if (res.status === 401) {
      // Token expired — clear and show logged-out state
      token = null; username = null; isAdmin = false;
       localStorage.removeItem('username');
      updateAuthUI(); updateAdminUI();
      el.innerHTML = '<p style="color:var(--muted);font-size:13px">Session expired. Please <a href="#" onclick="openAuthModal()" style="color:var(--accent)">log in again</a>.</p>';
      return;
    }
    const subs = await res.json();
    if (!window._submissionsCache) window._submissionsCache = {};
    subs.forEach(s => { window._submissionsCache[s.id] = s; });

    if (!subs.length) { el.innerHTML = '<p style="color:var(--muted);font-size:13px">No submissions yet. <a href="#" onclick="goTo(\'problems\')" style="color:var(--accent)">Try a problem →</a></p>'; return; }
    el.innerHTML = subs.map(s => {
      const hasCode = !!s.code;
      return `
      <div onclick="openSubmissionViewer(${s.id})" style="display:flex;align-items:center;gap:12px;padding:10px 8px;border-bottom:1px solid rgba(48,54,61,0.5);cursor:pointer;border-radius:6px" onmouseenter="this.style.background='rgba(88,166,255,0.05)'" onmouseleave="this.style.background=''">
        <span class="badge ${verdictClass(s.verdict || s.status)}">${formatVerdict(s.verdict || s.status)}</span>
        <span style="font-size:13px">Problem #${s.problem_id}</span>
        <span style="font-family:var(--mono);font-size:11px;color:var(--muted)">${s.language}</span>
        <span style="font-size:12px;color:var(--muted);margin-left:auto">${timeAgo(s.created_at)}</span>
        ${hasCode ? `<button onclick="event.stopPropagation();openSubmissionViewer(${s.id})" style="background:var(--surface2);border:1px solid var(--border);color:var(--accent);font-size:10px;padding:3px 10px;border-radius:6px;cursor:pointer">View</button>` : `<span style="color:var(--muted);font-size:11px;width:44px;text-align:center">—</span>`}
      </div>`;
    }).join('');
  } catch(e) {}
}
