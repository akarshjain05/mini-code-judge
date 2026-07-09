// ── Submission History ──────────────────────────────────────────────
// ── History ────────────────────────────────────────────────────────
async function loadHistory() {
  const tbody = document.getElementById('historyTable');
  if (!token) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:20px">Login to see your submissions.</td></tr>'; return; }
  tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:16px">Loading…</td></tr>';
  try {
    const res = await fetch(`${API}/submissions`, { headers: {} });
    const subs = await res.json();
    _allSubs = subs || [];

    // Cache submissions for the code viewer (always the FULL set, independent of filters)
    window._submissionsCache = {};
    _allSubs.forEach(s => { window._submissionsCache[s.id] = s; });

    // Update dashboard stats from the unfiltered list
    document.getElementById('dashStatTotal').textContent = _allSubs.length;
    document.getElementById('dashStatAccepted').textContent = _allSubs.filter(s => s.verdict === 'accepted').length;

    if (!_allSubs.length) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);padding:16px">No submissions yet.</td></tr>'; return; }

    // Populate language filter (distinct languages actually present)
    const langs = [...new Set(_allSubs.map(s => s.language).filter(Boolean))].sort();
    const langSel = document.getElementById('histFilterLang');
    if (langSel) {
      const prevLang = langSel.value;
      langSel.innerHTML = '<option value="">All Languages</option>' +
        langs.map(l => `<option value="${l}">${l.toUpperCase()}</option>`).join('');
      if (langs.includes(prevLang)) langSel.value = prevLang;
    }

    // Populate verdict filter (distinct verdicts/statuses actually present)
    const verdicts = [...new Set(_allSubs.map(s => s.verdict || s.status).filter(Boolean))].sort();
    const verdictSel = document.getElementById('histFilterVerdict');
    if (verdictSel) {
      const prevVerdict = verdictSel.value;
      verdictSel.innerHTML = '<option value="">All Verdicts</option>' +
        verdicts.map(v => `<option value="${v}">${formatVerdict(v)}</option>`).join('');
      if (verdicts.includes(prevVerdict)) verdictSel.value = prevVerdict;
    }

    filterHistory();
  } catch(e) { tbody.innerHTML = '<tr><td colspan="7" style="color:var(--warn);padding:16px">⚠ Error loading submissions.</td></tr>'; }
}

function filterHistory() {
  const tbody = document.getElementById('historyTable');
  if (!tbody) return;

  const search  = (document.getElementById('histSearch')?.value || '').trim().toLowerCase();
  const lang    = document.getElementById('histFilterLang')?.value || '';
  const verdict = document.getElementById('histFilterVerdict')?.value || '';

  const filtered = _allSubs.filter(s => {
    if (lang && s.language !== lang) return false;
    if (verdict && (s.verdict || s.status) !== verdict) return false;
    if (search) {
      const probMatch = String(s.problem_id).includes(search) || `problem #${s.problem_id}`.toLowerCase().includes(search);
      const idMatch = String(s.id).includes(search);
      if (!probMatch && !idMatch) return false;
    }
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:var(--muted);padding:16px">${_allSubs.length ? 'No submissions match your filters.' : 'No submissions yet.'}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
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
}

function clearHistoryFilters() {
  const s = document.getElementById('histSearch'); if (s) s.value = '';
  const l = document.getElementById('histFilterLang'); if (l) l.value = '';
  const v = document.getElementById('histFilterVerdict'); if (v) v.value = '';
  filterHistory();
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
