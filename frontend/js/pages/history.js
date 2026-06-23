// ── Submission History ──────────────────────────────────────────────
// ── History ────────────────────────────────────────────────────────
async function loadHistory() {
  const tbody = document.getElementById('historyTable');
  if (!token) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:20px">Login to see your submissions.</td></tr>'; return; }
  tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:16px">Loading…</td></tr>';
  try {
    const res = await fetch(`${API}/submissions`, { headers: { 'Authorization': `Bearer ${token}` } });
    const subs = await res.json();
    if (!subs.length) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:16px">No submissions yet.</td></tr>'; return; }
    tbody.innerHTML = subs.map(s => {
      const submittedAt = s.created_at ? timeAgo(s.created_at) : '—';
      const hasCode = !!s.code;
      return `
      <tr onclick="openSubmissionViewer(${s.id})" style="cursor:pointer" title="Click to view submitted code" onmouseenter="this.style.background='rgba(88,166,255,0.05)'" onmouseleave="this.style.background=''">
        <td style="font-family:var(--mono);color:var(--muted)">#${s.id}</td>
        <td style="font-weight:500">Problem #${s.problem_id}</td>
        <td><span style="font-family:var(--mono);font-size:12px;color:var(--muted)">${s.language}</span></td>
        <td><span class="badge ${verdictClass(s.verdict || s.status)}">${formatVerdict(s.verdict || s.status)}</span></td>
        <td style="font-family:var(--mono);font-size:12px">${s.runtime_ms ? s.runtime_ms.toFixed(1)+' ms' : '—'}</td>
        <td style="color:var(--muted);font-size:12px">${submittedAt}</td>
        <td style="text-align:center">
          ${hasCode
            ? `<button onclick="event.stopPropagation();openSubmissionViewer(${s.id})" style="background:var(--surface2);border:1px solid var(--border);color:var(--accent);font-size:10px;padding:3px 10px;border-radius:6px;cursor:pointer">View</button>`
            : `<span style="color:var(--muted);font-size:11px">—</span>`}
        </td>
      </tr>`;
    }).join('');

    // Cache submissions for viewer
    window._submissionsCache = {};
    subs.forEach(s => { window._submissionsCache[s.id] = s; });

    // Update dashboard stats
    document.getElementById('dashStatTotal').textContent = subs.length;
    document.getElementById('dashStatAccepted').textContent = subs.filter(s => s.verdict === 'accepted').length;
  } catch(e) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--warn);padding:16px">⚠ Error loading submissions.</td></tr>'; }
}

function openSubmissionViewer(id) {
  const s = window._submissionsCache && window._submissionsCache[id];
  if (!s) return;
  document.getElementById('cvTitle').textContent = `Submission #${s.id} — Problem #${s.problem_id}`;
  const submittedAt = s.created_at ? new Date(s.created_at).toLocaleString('en-IN', {timeZone:'Asia/Kolkata'}) : 'Unknown time';
  document.getElementById('cvMeta').textContent = submittedAt + ' IST';
  const vEl = document.getElementById('cvVerdict');
  vEl.textContent = formatVerdict(s.verdict || s.status);
  vEl.className = 'badge ' + verdictClass(s.verdict || s.status);
  document.getElementById('cvLang').textContent = s.language ? s.language.toUpperCase() : '—';
  document.getElementById('cvRuntime').textContent = s.runtime_ms ? s.runtime_ms.toFixed(1) + ' ms' : 'N/A';
  document.getElementById('cvCode').textContent = s.code || '// Code not available\n// (older submissions may not have code stored)';
  const modal = document.getElementById('codeViewerModal');
  modal.style.display = 'flex';
  history.pushState({ page: 'submission', id }, '', '#submission/' + id);
}

function openAdminSubmissionViewer(id) {
  const s = window._adminSubsCache && window._adminSubsCache[id];
  if (!s) return;
  document.getElementById('cvTitle').textContent = `Submission #${s.id} — ${s.username} — Problem #${s.problem_id}`;
  const submittedAt = s.created_at ? new Date(s.created_at).toLocaleString('en-IN', {timeZone:'Asia/Kolkata'}) : 'Unknown time';
  document.getElementById('cvMeta').textContent = submittedAt + ' IST';
  const vEl = document.getElementById('cvVerdict');
  vEl.textContent = formatVerdict(s.verdict || s.status);
  vEl.className = 'badge ' + verdictClass(s.verdict || s.status);
  document.getElementById('cvLang').textContent = s.language ? s.language.toUpperCase() : '—';
  document.getElementById('cvRuntime').textContent = s.runtime_ms ? s.runtime_ms.toFixed(1) + ' ms' : 'N/A';
  document.getElementById('cvCode').textContent = s.code || '// Code not available';
  const modal = document.getElementById('codeViewerModal');
  modal.style.display = 'flex';
  history.pushState({ page: 'admin-submission', id }, '', '#admin');
}

function closeCodeViewer() {
  document.getElementById('codeViewerModal').style.display = 'none';
  history.back();
}

function copySubmissionCode() {
  const code = document.getElementById('cvCode').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById('cvCopyBtn');
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy Code'; }, 1800);
  });
}

function verdictClass(v) {
  if (v === 'accepted') return 'badge-accepted';
  if (v === 'wrong_answer') return 'badge-wrong';
  if (v === 'pending' || v === 'running') return 'badge-running';
  return 'badge-error';
}
