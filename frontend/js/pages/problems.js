// ── Problems Page ───────────────────────────────────────────────────
// ── Problems ───────────────────────────────────────────────────────
let _problemAcceptance = {}; // problem_id -> { total, accepted }

async function loadProblems(retriesLeft = 2) {
  const tbody = document.getElementById('problemList');
  try {
    const [probRes, subRes] = await Promise.all([
      fetch(`${API}/problems`),
      token ? fetch(`${API}/leaderboard/submissions`) : Promise.resolve(null),
    ]);
    const problems = await probRes.json();
    _allProblems = problems;
    document.getElementById('statProblems').textContent = problems.length;

    // Build acceptance rates from all submissions
    _problemAcceptance = {};
    if (subRes && subRes.ok) {
      const subs = await subRes.json();
      subs.forEach(s => {
        if (!_problemAcceptance[s.problem_id]) _problemAcceptance[s.problem_id] = { total: 0, accepted: 0 };
        _problemAcceptance[s.problem_id].total++;
        if (s.verdict === 'accepted') _problemAcceptance[s.problem_id].accepted++;
      });
    }

    // Populate category filter (problems can have multiple comma-separated categories)
    const catSet = new Set();
    problems.forEach(p => (p.category || '').split(',').map(c => c.trim()).filter(Boolean).forEach(c => catSet.add(c)));
    const cats = [...catSet].sort();
    const catSel = document.getElementById('probFilterCat');
    catSel.innerHTML = '<option value="">All Categories</option>' +
      cats.map(c => `<option value="${c}">${c}</option>`).join('');

    filterProblems();
  } catch(e) {
    // Render's free tier spins the backend down after inactivity — the very
    // first request can fail while it wakes up. Retry quietly before
    // showing an error, so users don't see a scary message unnecessarily.
    if (retriesLeft > 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding:24px;color:var(--muted)">⏳ Waking up server… this can take up to a minute on first load.</td></tr>';
      await new Promise(r => setTimeout(r, 4000));
      return loadProblems(retriesLeft - 1);
    }
    tbody.innerHTML = '<tr><td colspan="5" style="padding:24px;color:var(--warn)">⚠ Cannot reach API. Please refresh the page.</td></tr>';
  }
}

function filterProblems() {
  const tbody = document.getElementById('problemList');
  const search = (document.getElementById('probSearch')?.value || '').toLowerCase();
  const diff   = document.getElementById('probFilterDiff')?.value || '';
  const cat    = document.getElementById('probFilterCat')?.value || '';

  const filtered = _allProblems.filter(p => {
    if (diff && p.difficulty !== diff) return false;
    if (cat) {
      const probCats = (p.category || '').split(',').map(c => c.trim());
      if (!probCats.includes(cat)) return false;
    }
    if (search && !p.title.toLowerCase().includes(search) && !(p.category||'').toLowerCase().includes(search)) return false;
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding:24px;color:var(--muted)">No problems match your filters.</td></tr>';
    return;
  }

  const isAdmin = document.getElementById('adminBadge')?.style.display !== 'none';
  tbody.innerHTML = filtered.map((p, i) => {
    const acc = _problemAcceptance[p.id];
    const rate = acc && acc.total > 0 ? Math.round((acc.accepted/acc.total)*100) : null;
    const rateColor = rate === null ? 'var(--muted)' : rate >= 70 ? '#4ade80' : rate >= 40 ? '#f59e0b' : '#ef4444';
    const catList = (p.category || '').split(',').map(c => c.trim()).filter(Boolean);
    const catBadge = catList.length
      ? `<div style="display:flex;flex-wrap:wrap;gap:4px;justify-content:center">${catList.map(c => `<span style="font-size:10px;background:rgba(88,166,255,0.12);color:var(--accent);padding:2px 8px;border-radius:8px;border:1px solid rgba(88,166,255,0.2);white-space:nowrap">${c}</span>`).join('')}</div>`
      : '<span style="color:var(--muted);font-size:11px">—</span>';
    return `<tr onclick="openProblem(${JSON.stringify(p).replace(/"/g,'&quot;')})"
      style="cursor:pointer;border-bottom:1px solid var(--border);transition:background 0.1s"
      onmouseover="this.style.background='rgba(88,166,255,0.04)'" onmouseout="this.style.background=''">
      <td style="padding:12px 16px;font-family:var(--mono);color:var(--muted);font-size:12px">${p.id}</td>
      <td style="padding:12px 16px">
        <div style="font-weight:600;font-size:13px;color:var(--text)">${p.title}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${(p.description||'').slice(0,60)}${(p.description||'').length>60?'…':''}</div>
      </td>
      <td style="padding:12px 16px;text-align:center">${catBadge}</td>
      <td style="padding:12px 16px;text-align:center"><span class="badge badge-${p.difficulty}">${p.difficulty}</span></td>
      <td style="padding:12px 16px;text-align:center;font-weight:600;color:${rateColor};font-size:13px">
        ${rate !== null ? rate+'%' : '<span style="color:var(--muted)">—</span>'}
        ${acc ? `<div style="font-size:10px;color:var(--muted);font-weight:400">${acc.accepted}/${acc.total}</div>` : ''}
      </td>
    </tr>
    ${isAdmin ? `<tr style="border-bottom:1px solid var(--border);background:rgba(0,0,0,0.15)">
      <td colspan="5" style="padding:4px 16px;text-align:right">
        <button onclick="event.stopPropagation();editProblem(${JSON.stringify(p).replace(/"/g,'&quot;')})" style="background:none;border:none;color:var(--accent);font-size:11px;cursor:pointer;padding:2px 8px">✏ Edit</button>
      </td>
    </tr>` : ''}`;
  }).join('');
}
function openProblem(p) {
  // Fully reset the code editor, verdict box, and AI review panel first —
  // otherwise stale state (code, verdict, "Analyzing…") from whatever
  // problem/submission was last viewed leaks into this fresh screen.
  resetSubmitScreen();

  currentProblem = p;
  document.getElementById('submitProblemTitle').textContent = `#${p.id} — ${p.title}`;
  document.getElementById('submitProblemDesc').textContent = p.description;
  const diffBadge = document.getElementById('submitDiffBadge');
  diffBadge.textContent = p.difficulty;
  diffBadge.className = `badge badge-${p.difficulty}`;
  loadSampleTestCases(p.id);
  goTo('submit', false);
  history.pushState({ page: 'submit', problem_id: p.id }, '', '#problem/' + p.id);
}
