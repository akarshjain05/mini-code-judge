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
      localStorage.removeItem('token');
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
      // Attempt to look up the problem title
      const p = window._problemsData ? window._problemsData.find(p => p.id === s.problem_id) : null;
      const pTitle = p ? p.title : 'Problem';
      
      return `
      <div onclick="openSubmissionViewer(${s.id})" style="display:flex;align-items:center;gap:12px;padding:16px 24px;border-bottom:1px solid rgba(48,54,61,0.5);cursor:pointer;" onmouseenter="this.style.background='rgba(88,166,255,0.05)'" onmouseleave="this.style.background=''">
        <div style="flex:1;font-size:14px;color:var(--text);font-weight:500;">Problem #${s.problem_id}: ${pTitle}</div>
        <div style="width:100px;font-family:var(--mono);font-size:13px;color:var(--muted);">${s.language === 'python' ? 'Python' : s.language === 'cpp' ? 'C++' : s.language === 'java' ? 'Java' : s.language}</div>
        <div style="width:180px;">
          <span class="badge ${verdictClass(s.verdict || s.status)}" style="padding:4px 10px; border-radius: 12px; font-weight: 500;">${formatVerdict(s.verdict || s.status)}</span>
        </div>
        <div style="width:120px;font-size:13px;color:var(--muted);">${timeAgo(s.created_at)}</div>
        <div>
          ${hasCode ? `<button onclick="event.stopPropagation();openSubmissionViewer(${s.id})" style="background:transparent;border:1px solid var(--border);color:var(--text);font-size:12px;padding:5px 16px;border-radius:20px;cursor:pointer;" onmouseenter="this.style.background='var(--border)'" onmouseleave="this.style.background='transparent'">View</button>` : `<span style="color:var(--muted);font-size:11px;width:44px;text-align:center">—</span>`}
        </div>
      </div>`;
    }).join('');
  } catch(e) {}
}
