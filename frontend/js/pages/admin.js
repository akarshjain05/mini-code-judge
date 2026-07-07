// ── Admin Dashboard ─────────────────────────────────────────────────
async function loadAdminDashboard() {
  if ((username || localStorage.getItem('username')) !== 'akarsh') return;
  try {
    const usersRes = await fetch(`${API}/admin/users`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (usersRes.ok) {
      const users = await usersRes.json();
      document.getElementById('adminUsersList').innerHTML = `<table style="width:100%;font-size:12px">
        <thead><tr><th style="text-align:left;padding:4px 6px;color:var(--muted)">#</th><th style="text-align:left;padding:4px 6px;color:var(--muted)">Username</th><th style="text-align:left;padding:4px 6px;color:var(--muted)">Email</th><th style="text-align:left;padding:4px 6px;color:var(--muted)">Joined</th></tr></thead>
        <tbody>${users.map(u => `<tr><td style="padding:4px 6px;color:var(--muted)">${u.id}</td><td style="padding:4px 6px;font-weight:600">${u.username}</td><td style="padding:4px 6px;color:var(--muted)">${u.email}</td><td style="padding:4px 6px;color:var(--muted);font-size:11px">${timeAgo(u.created_at)}</td></tr>`).join('')}</tbody>
      </table>`;
    }
    const subsRes = await fetch(`${API}/admin/submissions`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (subsRes.ok) {
      const subs = await subsRes.json();
      const accepted = subs.filter(s => s.verdict === 'accepted').length;
      document.getElementById('adminStatsBox').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div style="background:var(--surface2);border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:24px;font-weight:700">${subs.length}</div><div style="font-size:11px;color:var(--muted)">Total Submissions</div>
          </div>
          <div style="background:var(--surface2);border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:24px;font-weight:700;color:var(--accent2)">${accepted}</div><div style="font-size:11px;color:var(--muted)">Accepted</div>
          </div>
        </div>`;
      document.getElementById('adminSubsTable').innerHTML = subs.length
        ? subs.map(s => `<tr onclick="openAdminSubmissionViewer(${s.id})" style="cursor:pointer" onmouseenter="this.style.background='rgba(88,166,255,0.05)'" onmouseleave="this.style.background=''">
            <td style="font-family:var(--mono);color:var(--muted)">#${s.id}</td>
            <td style="font-weight:600">${s.username || s.user_id}</td>
            <td>Problem #${s.problem_id}</td>
            <td><span style="font-family:var(--mono);font-size:12px;color:var(--muted)">${s.language}</span></td>
            <td><span class="badge ${verdictClass(s.verdict || s.status)}">${formatVerdict(s.verdict || s.status)}</span></td>
            <td style="font-family:var(--mono);font-size:12px">${s.runtime_ms ? s.runtime_ms.toFixed(1)+' ms' : '—'}</td>
            <td style="color:var(--muted);font-size:11px">${timeAgo(s.created_at)}</td>
            <td style="text-align:center">${s.code ? `<button onclick="event.stopPropagation();openAdminSubmissionViewer(${s.id})" style="background:var(--surface2);border:1px solid var(--border);color:var(--accent);font-size:10px;padding:3px 10px;border-radius:6px;cursor:pointer">View</button>` : '<span style="color:var(--muted);font-size:11px">—</span>'}</td>
          </tr>`).join('')
        : '<tr><td colspan="8" style="color:var(--muted);padding:16px">No submissions yet.</td></tr>';

      // Cache for the code viewer modal
      window._adminSubsCache = {};
      subs.forEach(s => { window._adminSubsCache[s.id] = s; });
    }
  } catch(e) {
    document.getElementById('adminUsersList').innerHTML = '<p style="color:var(--warn)">⚠ Error loading data. Check if admin endpoints are deployed.</p>';
  }
}


// ── AI Code Review ──────────────────────────────────────────────────
async function requestAIReview() {
  const btn = document.getElementById('aiReviewBtn');
  const panel = document.getElementById('aiReviewPanel');
  const content = document.getElementById('aiReviewContent');

  btn.disabled = true;
  btn.textContent = '🤖 Analyzing…';
  panel.style.display = 'block';
  // Set the loading state directly rather than looking up a previous
  // #aiReviewLoading node — after the first review (success OR failure),
  // this innerHTML is replaced, so that node no longer exists. Looking it
  // up and touching .style on it crashed with "Cannot read properties of
  // null" on every retry/refresh click.
  content.innerHTML = '<div id="aiReviewLoading" style="display:flex;align-items:center;gap:10px;color:var(--muted)"><span class="spinner"></span> Analyzing your code with Claude AI…</div>';

  // Scroll to panel
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const subId = window._lastSubId;
    const res = await fetch(`${API}/submissions/${subId}/ai-review`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
      const err = await res.json();
      content.innerHTML = `<p style="color:var(--warn)">⚠ ${err.detail || 'AI review failed. Try again.'}</p>`;
      btn.disabled = false;
      btn.textContent = '🤖 Get AI Code Review';
      return;
    }

    const data = await res.json();
    renderAIReview(data.review, content);
    btn.textContent = '🤖 Refresh AI Review';
    btn.disabled = false;

  } catch(e) {
    content.innerHTML = '<p style="color:var(--warn)">⚠ Could not reach AI service. Try again.</p>';
    btn.disabled = false;
    btn.textContent = '🤖 Get AI Code Review';
  }
}

function renderAIReview(reviewText, container) {
  // Parse sections from the AI response and render nicely
  const sections = [
    { key: '## Complexity', icon: '⚡', label: 'Complexity Analysis', color: '#3b82f6' },
    { key: '## What Went Wrong', icon: '🔍', label: 'What Went Wrong', color: '#ef4444' },
    { key: '## Improvements', icon: '💡', label: 'Improvements', color: '#f59e0b' },
    { key: '## Alternative', icon: '🔄', label: 'Alternative Approach', color: '#10b981' },
    { key: '## Summary', icon: '📝', label: 'Summary', color: '#8b5cf6' },
  ];

  let html = '';
  let remaining = reviewText;

  sections.forEach((sec, i) => {
    const idx = remaining.indexOf(sec.key);
    if (idx === -1) return;
    const nextIdx = sections.slice(i+1).reduce((min, s) => {
      const p = remaining.indexOf(s.key, idx + sec.key.length);
      return (p !== -1 && p < min) ? p : min;
    }, remaining.length);
    const body = remaining.slice(idx + sec.key.length, nextIdx).trim();
    if (!body) return;
    // Convert markdown-like formatting
    const formatted = body
      .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:12px">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n- /g, '<br>• ')
      .replace(/\n/g, '<br>');
    html += `
      <div style="margin-bottom:16px;padding:12px;background:rgba(255,255,255,0.03);border-left:3px solid ${sec.color};border-radius:0 8px 8px 0">
        <div style="font-size:12px;font-weight:700;color:${sec.color};margin-bottom:6px;letter-spacing:0.5px">${sec.icon} ${sec.label.toUpperCase()}</div>
        <div style="color:var(--text);line-height:1.7">${formatted}</div>
      </div>`;
  });

  if (!html) {
    // Fallback: just render the raw text nicely
    const formatted = reviewText
      .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:12px">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    html = `<div style="line-height:1.7">${formatted}</div>`;
  }

  container.innerHTML = html;
}
