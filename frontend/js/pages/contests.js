// ── Contests Page ────────────────────────────────────────────────────
// ── Contest Mode ─────────────────────────────────────────────────────
let contestRefreshInterval = null;

function showJoinContest() {
  const box = document.getElementById('joinContestBox');
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
}

function showCreateContest() {
  const box = document.getElementById('createContestBox');
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
  // Set default start time to 5 minutes from now
  const d = new Date(Date.now() + 5 * 60000);
  d.setSeconds(0);
  document.getElementById('contestStart').value = d.toISOString().slice(0,16);
}

async function loadContests() {
  if (!token) { openAuthModal(); return; }
  if (contestRefreshInterval) clearInterval(contestRefreshInterval);
  await _fetchContests();
  contestRefreshInterval = setInterval(_fetchContests, 30000);
}

async function _fetchContests() {
  try {
    const res = await fetch(`${API}/contests`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) throw new Error();
    const contests = await res.json();
    renderContestsList(contests);
  } catch(e) {
    document.getElementById('contestsList').innerHTML = '<p style="color:var(--warn)">⚠ Error loading contests.</p>';
  }
}

function renderContestsList(contests) {
  const el = document.getElementById('contestsList');
  if (!contests.length) {
    el.innerHTML = `<div class="card" style="text-align:center;padding:40px">
      <div style="font-size:40px;margin-bottom:12px">🏆</div>
      <div style="font-weight:600;margin-bottom:8px">No contests yet</div>
      <div style="color:var(--muted);font-size:13px">Create a contest or join one with an invite code!</div>
    </div>`;
    return;
  }
  const statusColor = { live: '#4ade80', upcoming: '#f59e0b', ended: '#6b7280' };
  const statusIcon  = { live: '🔴 LIVE', upcoming: '⏳ Upcoming', ended: '✓ Ended' };

  // Group by status
  const groups = { live: [], upcoming: [], ended: [] };
  contests.forEach(c => (groups[c.status] || groups.ended).push(c));

  const renderGroup = (label, items) => {
    if (!items.length) return '';
    return `<div style="margin-bottom:20px">
      <div style="font-size:11px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:10px;text-transform:uppercase">${label}</div>
      ${items.map(c => `
        <div class="card" style="margin-bottom:10px;cursor:pointer;transition:border-color 0.15s"
          onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'"
          onclick="openContest(${c.id})">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <div style="font-weight:700;font-size:15px;margin-bottom:3px">${c.title}</div>
              <div style="font-size:12px;color:var(--muted)">
                ${new Date(c.starts_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} · ${c.duration_minutes} min
                ${c.is_mine ? ' · <span style="color:var(--accent)">Created by you</span>' : ''}
              </div>
            </div>
            <span style="font-size:11px;font-weight:700;color:${statusColor[c.status]};background:${statusColor[c.status]}22;padding:3px 12px;border-radius:10px;white-space:nowrap">
              ${statusIcon[c.status]}
            </span>
          </div>
        </div>`).join('')}
    </div>`;
  };

  el.innerHTML = renderGroup('🔴 Live Now', groups.live)
    + renderGroup('⏳ Upcoming', groups.upcoming)
    + renderGroup('✓ Past Contests', groups.ended);
}

async function openContest(id) {
  document.getElementById('contestsList').style.display = 'none';
  const detail = document.getElementById('contestDetail');
  detail.style.display = 'block';
  document.getElementById('contestDetailContent').innerHTML = '<p style="color:var(--muted)">Loading…</p>';
  history.pushState({ page: 'contest', id }, '', '#contest/' + id);

  try {
    const res = await fetch(`${API}/contests/${id}`, { headers: { 'Authorization': `Bearer ${token}` } });
    const c = await res.json();
    renderContestDetail(c);
    if (c.status === 'live') {
      if (contestRefreshInterval) clearInterval(contestRefreshInterval);
      contestRefreshInterval = setInterval(async () => {
        const r = await fetch(`${API}/contests/${id}/leaderboard`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (r.ok) { const lb = await r.json(); renderLeaderboard(lb, c.problems, document.getElementById('liveLeaderboard')); }
      }, 30000);
    }
  } catch(e) {
    document.getElementById('contestDetailContent').innerHTML = '<p style="color:var(--warn)">⚠ Error loading contest.</p>';
  }
}

function renderContestDetail(c) {
  const now    = new Date();
  const starts = new Date(c.starts_at);
  const ends   = new Date(c.ends_at);
  const statusColor = { live: '#4ade80', upcoming: '#f59e0b', ended: '#6b7280' };

  let countdown = '';
  if (c.status === 'live') {
    const rem = Math.max(0, ends - now);
    const h = Math.floor(rem/3600000), m = Math.floor((rem%3600000)/60000), s = Math.floor((rem%60000)/1000);
    countdown = `<div id="contestCountdown" style="font-size:24px;font-weight:800;color:#4ade80;font-family:var(--mono)">${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}</div><div style="font-size:11px;color:var(--muted)">Time remaining</div>`;
  } else if (c.status === 'upcoming') {
    const rem = Math.max(0, starts - now);
    const h = Math.floor(rem/3600000), m = Math.floor((rem%3600000)/60000);
    countdown = `<div style="font-size:18px;font-weight:700;color:#f59e0b">Starts in ${h}h ${m}m</div>`;
  } else {
    countdown = `<div style="font-size:14px;color:var(--muted)">Ended ${timeAgo(c.ends_at)}</div>`;
  }

  // Problems section — hidden before contest starts; visible during and after
  let problemsHTML = '';
  if (c.status === 'upcoming' && !c.is_mine) {
    problemsHTML = `<div class="card" style="margin-bottom:18px;text-align:center;padding:28px">
      <div style="font-size:28px;margin-bottom:8px">🔒</div>
      <div style="font-weight:600;margin-bottom:4px">Problems are hidden</div>
      <div style="color:var(--muted);font-size:13px">Problems will be revealed when the contest starts.</div>
    </div>`;
  } else {
    const canSolve = c.status === 'live' && c.is_joined;
    const canPractice = c.status === 'ended';
    problemsHTML = `<div class="card" style="margin-bottom:18px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <div class="card-title" style="margin:0">📋 Problems</div>
        ${canPractice ? '<span style="font-size:11px;color:#f59e0b;background:#f59e0b22;padding:2px 10px;border-radius:8px">Practice mode — contest has ended</span>' : ''}
      </div>
      ${c.problems.map((p, i) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)">
          <div>
            <span style="font-weight:600">${String.fromCharCode(65+i)}. ${p.title}</span>
            <span class="badge badge-${p.difficulty}" style="margin-left:8px">${p.difficulty}</span>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:12px;color:var(--accent);font-weight:600">${p.points} pts</span>
            ${canSolve || canPractice ? `<button onclick="openProblemForContest(${p.id}, ${c.id})" class="btn ${canPractice ? 'btn-ghost' : 'btn-success'}" style="padding:5px 14px;font-size:12px">${canPractice ? 'Practice' : 'Solve'}</button>` : ''}
          </div>
        </div>`).join('')}
    </div>`;
  }

  document.getElementById('contestDetailContent').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr auto;gap:18px;align-items:start;margin-bottom:18px">
      <div>
        <h2 style="margin:0 0 6px;font-size:22px">${c.title}</h2>
        <div style="font-size:13px;color:var(--muted);margin-bottom:8px">${c.description || ''}</div>
        <div style="display:flex;gap:16px;font-size:12px;color:var(--muted);flex-wrap:wrap">
          <span>⏱ ${c.duration_minutes} min</span>
          <span>👥 ${c.participants} participants</span>
          <span>📋 ${c.problems.length} problems</span>
          <span>🔗 Code: <code style="color:var(--accent);cursor:pointer" onclick="navigator.clipboard.writeText('${c.invite_code}')" title="Click to copy">${c.invite_code}</code></span>
        </div>
      </div>
      <div style="text-align:center;background:var(--surface2);padding:14px 20px;border-radius:10px;min-width:140px">
        <div style="font-size:11px;font-weight:700;color:${statusColor[c.status]};margin-bottom:6px">${c.status.toUpperCase()}</div>
        ${countdown}
      </div>
    </div>

    ${!c.is_joined ? `
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:18px;display:flex;align-items:center;justify-content:space-between">
      <div>
        <div style="font-weight:600;margin-bottom:2px">You haven't joined this contest</div>
        <div style="font-size:12px;color:var(--muted)">${c.status === 'ended' ? 'You can still join to practice the problems.' : 'Join to participate and appear on the leaderboard.'}</div>
      </div>
      <button class="btn btn-success" onclick="joinContest('${c.invite_code}', ${c.id})" style="padding:10px 20px;white-space:nowrap">Join Contest</button>
    </div>` : ''}

    ${problemsHTML}

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <div class="card-title" style="margin:0">🏆 Leaderboard</div>
        ${c.status === 'live' ? '<span style="font-size:11px;color:var(--accent)">🔴 Updates every 30s</span>' : ''}
      </div>
      <div id="liveLeaderboard">${renderLeaderboardHTML(c.leaderboard, c.problems)}</div>
    </div>`;

  // Live countdown ticker
  if (c.status === 'live') {
    const endTime = new Date(c.ends_at);
    const timer = setInterval(() => {
      const rem = Math.max(0, endTime - new Date());
      if (rem === 0) { clearInterval(timer); return; }
      const h = Math.floor(rem/3600000), m = Math.floor((rem%3600000)/60000), s = Math.floor((rem%60000)/1000);
      const el = document.getElementById('contestCountdown');
      if (el) el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      else clearInterval(timer);
    }, 1000);
  }
}

function renderLeaderboard(lb, problems, container) {
  if (container) container.innerHTML = renderLeaderboardHTML(lb, problems);
}

function renderLeaderboardHTML(lb, problems) {
  if (!lb.length) return '<p style="color:var(--muted);font-size:13px">No participants yet.</p>';
  return `<table style="width:100%;font-size:13px;border-collapse:collapse">
    <thead><tr style="border-bottom:1px solid var(--border)">
      <th style="text-align:left;padding:8px 6px;color:var(--muted)">#</th>
      <th style="text-align:left;padding:8px 6px;color:var(--muted)">User</th>
      ${problems.map((p,i) => `<th style="text-align:center;padding:8px 6px;color:var(--muted)">${String.fromCharCode(65+i)}</th>`).join('')}
      <th style="text-align:right;padding:8px 6px;color:var(--muted)">Score</th>
      <th style="text-align:right;padding:8px 6px;color:var(--muted)">Penalty</th>
    </tr></thead>
    <tbody>${lb.map(row => `
      <tr style="border-bottom:1px solid var(--border)">
        <td style="padding:8px 6px;font-weight:700;color:${['#ffd700','#c0c0c0','#cd7f32'][row.rank-1]||'var(--text)'}">${row.rank<=3?['🥇','🥈','🥉'][row.rank-1]:'#'+row.rank}</td>
        <td style="padding:8px 6px;font-weight:600">${row.username}</td>
        ${problems.map(p => {
          const ps = row.problem_status[p.id];
          if (!ps||ps.status==='none') return '<td style="text-align:center;padding:8px 6px;color:var(--muted)">—</td>';
          if (ps.status==='accepted') return `<td style="text-align:center;padding:8px 6px"><span style="color:#4ade80;font-weight:600">✓${ps.attempts>1?' +'+( ps.attempts-1):''}</span></td>`;
          return `<td style="text-align:center;padding:8px 6px"><span style="color:#ef4444">✗${ps.attempts}</span></td>`;
        }).join('')}
        <td style="text-align:right;padding:8px 6px;font-weight:700;color:var(--accent2)">${row.points}</td>
        <td style="text-align:right;padding:8px 6px;color:var(--muted)">${row.penalty}</td>
      </tr>`).join('')}
    </tbody></table>`;
}

async function joinContest(inviteCode, contestId) {
  try {
    const res = await fetch(`${API}/contests/join/${inviteCode}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    const d = await res.json();
    if (!res.ok) { alert(d.detail || 'Failed to join'); return; }
    openContest(contestId);
  } catch(e) { alert('Failed to join contest'); }
}

async function joinByCode() {
  const code = document.getElementById('inviteCodeInput').value.trim();
  if (!code) { alert('Please enter an invite code'); return; }
  if (!token) { openAuthModal(); return; }
  try {
    const res = await fetch(`${API}/contests/join/${code}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    const d = await res.json();
    if (!res.ok) { alert(d.detail || 'Invalid invite code'); return; }
    document.getElementById('joinContestBox').style.display = 'none';
    openContest(d.contest_id);
  } catch(e) { alert('Invalid invite code'); }
}

async function createContest() {
  const title = document.getElementById('contestTitle').value.trim();
  const duration = parseInt(document.getElementById('contestDuration').value);
  const start = document.getElementById('contestStart').value;
  const problemIds = document.getElementById('contestProblems').value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));

  if (!title || !start || !problemIds.length) {
    alert('Please fill in all fields'); return;
  }

  try {
    const res = await fetch(`${API}/contests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        title, duration_minutes: duration,
        starts_at: new Date(start).toISOString(),
        problem_ids: problemIds,
      })
    });
    const d = await res.json();
    if (!res.ok) { alert(d.detail); return; }
    document.getElementById('createContestResult').innerHTML = `
      <div style="padding:14px;background:rgba(74,222,128,0.1);border:1px solid #4ade80;border-radius:8px">
        <div style="font-weight:700;color:#4ade80;margin-bottom:6px">✓ Contest Created!</div>
        <div style="font-size:13px;color:var(--text)">Invite code: <code style="background:var(--surface2);padding:2px 8px;border-radius:4px;font-size:14px;color:var(--accent)">${d.invite_code}</code></div>
        <div style="font-size:12px;color:var(--muted);margin-top:6px">Share this code with your friends to join!</div>
        <button onclick="document.getElementById('createContestBox').style.display='none';loadContests()" class="btn btn-success" style="margin-top:10px;padding:6px 16px;font-size:12px">View Contest</button>
      </div>`;
  } catch(e) { alert('Failed to create contest'); }
}

function openProblemForContest(problemId, contestId) {
  // Load problem and open submit page
  fetch(`${API}/problems/${problemId}`)
    .then(r => r.json())
    .then(p => { openProblem(p); })
    .catch(() => alert('Failed to load problem'));
}
