// ── Leaderboard Page ────────────────────────────────────────────────
// ── Leaderboard ────────────────────────────────────────────────────

async function loadLeaderboard() {
  const tbody = document.getElementById('lbTableBody');
  tbody.innerHTML = '<tr><td colspan="10" style="padding:28px;color:var(--muted);text-align:center">Loading…</td></tr>';

  try {
    // Fetch all we need in parallel
    const [subsRes, probsRes, usersRes] = await Promise.all([
      fetch(`${API}/leaderboard/submissions`),
      fetch(`${API}/problems`),
      fetch(`${API}/leaderboard/users`),
    ]);

    // If the dedicated leaderboard endpoints don't exist yet, fall back gracefully
    if (!subsRes.ok || !probsRes.ok) {
      tbody.innerHTML = '<tr><td colspan="10" style="padding:28px;color:var(--warn);text-align:center">⚠ Leaderboard backend not set up yet — see instructions below table.</td></tr>';
      return;
    }

    const allSubs = await subsRes.json();
    const problems = probsRes.ok ? await probsRes.json() : [];
    const users    = usersRes.ok ? await usersRes.json() : [];

    // Build problem id → difficulty map
    const probMap = {};
    problems.forEach(p => { probMap[p.id] = (p.difficulty || 'unknown').toLowerCase(); });

    // Group submissions by user
    const byUser = {};
    allSubs.forEach(s => {
      if (!byUser[s.user_id]) byUser[s.user_id] = { user_id: s.user_id, username: s.username || `user${s.user_id}`, subs: [] };
      byUser[s.user_id].subs.push(s);
    });

    // Build leaderboard rows
    _lbData = Object.values(byUser).map(u => {
      const subs = u.subs;
      const total = subs.length;
      const accepted = subs.filter(s => s.verdict === 'accepted').length;
      const accuracy = total ? Math.round((accepted / total) * 100) : 0;

      // Unique solved by difficulty
      const solvedIds = { easy: new Set(), medium: new Set(), hard: new Set(), unknown: new Set() };
      subs.filter(s => s.verdict === 'accepted').forEach(s => {
        const diff = probMap[s.problem_id] || 'unknown';
        if (solvedIds[diff]) solvedIds[diff].add(s.problem_id);
        else solvedIds.unknown.add(s.problem_id);
      });
      const solved = solvedIds.easy.size + solvedIds.medium.size + solvedIds.hard.size + solvedIds.unknown.size;

      // Streak in IST
      const acceptedDaySet = new Set(
        subs.filter(s => s.verdict === 'accepted').map(s => toISTDateKey(s.created_at)).filter(Boolean)
      );
      let streak = 0;
      const nowIST2 = toIST(new Date().toISOString());
      for (let i = 0; i < 365; i++) {
        const d = new Date(nowIST2.getTime() - i * 86400000);
        const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}`;
        if (acceptedDaySet.has(key)) streak++;
        else if (i > 0) break;
      }

      // Languages used
      const langs = [...new Set(subs.map(s => s.language).filter(Boolean))];

      return {
        user_id: u.user_id,
        username: u.username,
        solved,
        total,
        accepted,
        accuracy,
        easy: solvedIds.easy.size,
        medium: solvedIds.medium.size,
        hard: solvedIds.hard.size,
        streak,
        langs,
      };
    });

    // Update summary bar
    document.getElementById('lbTotalUsers').textContent = _lbData.length;
    document.getElementById('lbTotalSubs').textContent = allSubs.length;
    document.getElementById('lbTotalProbs').textContent = problems.length;

    lbSort(_lbSortKey);
  } catch(e) {
    console.error('Leaderboard error:', e);
    tbody.innerHTML = `<tr><td colspan="10" style="padding:28px;color:var(--warn);text-align:center">⚠ ${e.message}</td></tr>`;
  }
}

function lbSort(key) {
  _lbSortKey = key;
  // Highlight active sort button
  ['lbSortSolved','lbSortAccuracy','lbSortStreak'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.style.background = 'none';
  });
  const activeId = { solved:'lbSortSolved', accuracy:'lbSortAccuracy', streak:'lbSortStreak' }[key];
  if (activeId) document.getElementById(activeId).style.background = 'rgba(88,166,255,0.12)';

  const sorted = [..._lbData].sort((a, b) => {
    if (key === 'solved')   return b.solved   - a.solved   || b.accuracy - a.accuracy;
    if (key === 'accuracy') return b.accuracy - a.accuracy || b.solved   - a.solved;
    if (key === 'streak')   return b.streak   - a.streak   || b.solved   - a.solved;
    return 0;
  });

  const me = localStorage.getItem('username') || '';
  const medals = ['🥇','🥈','🥉'];
  const langColors = { cpp:'#3b82f6', python:'#f59e0b', java:'#ef4444', c:'#10b981' };

  document.getElementById('lbTableBody').innerHTML = sorted.map((u, i) => {
    const rank = i + 1;
    const isMe = u.username === me;
    const medal = rank <= 3 ? medals[rank - 1] : rank;
    const rowStyle = isMe ? 'background:rgba(88,166,255,0.07);' : '';
    const nameSuffix = isMe ? ' <span style="font-size:10px;color:var(--accent);margin-left:4px">(you)</span>' : '';
    const avatarBg = isMe ? 'var(--accent)' : '#444';

    const langBadges = u.langs.slice(0, 4).map(l => {
      const c = langColors[l] || '#8b5cf6';
      return `<span style="font-size:9px;background:${c}22;color:${c};border:1px solid ${c}44;padding:1px 6px;border-radius:8px">${l.toUpperCase()}</span>`;
    }).join(' ');

    const streakDisplay = u.streak > 0
      ? `<span style="color:#f59e0b">🔥 ${u.streak}</span>`
      : `<span style="color:var(--muted)">—</span>`;

    const accColor = u.accuracy >= 80 ? '#4ade80' : u.accuracy >= 50 ? '#f59e0b' : '#ef4444';

    return `<tr style="${rowStyle}cursor:default">
      <td style="text-align:center;font-size:${rank<=3?'20':'14'}px;font-weight:700">${medal}</td>
      <td>
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:30px;height:30px;border-radius:50%;background:${avatarBg};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#fff;flex-shrink:0">
            ${u.username[0].toUpperCase()}
          </div>
          <div>
            <div style="font-weight:600;font-size:13px;color:var(--text)">${u.username}${nameSuffix}</div>
            <div style="font-size:10px;color:var(--muted)">${u.total} submission${u.total!==1?'s':''}</div>
          </div>
        </div>
      </td>
      <td style="text-align:center;font-size:16px;font-weight:700;color:var(--accent2)">${u.solved}</td>
      <td style="text-align:center;font-size:13px;color:var(--muted)">${u.total}</td>
      <td style="text-align:center;font-weight:700;color:${accColor}">${u.accuracy}%</td>
      <td style="text-align:center;color:#4ade80;font-weight:600">${u.easy || '—'}</td>
      <td style="text-align:center;color:#f59e0b;font-weight:600">${u.medium || '—'}</td>
      <td style="text-align:center;color:#ef4444;font-weight:600">${u.hard || '—'}</td>
      <td style="text-align:center">${streakDisplay}</td>
      <td style="text-align:center">${langBadges || '<span style="color:var(--muted);font-size:11px">—</span>'}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="10" style="padding:28px;color:var(--muted);text-align:center">No data yet</td></tr>';
}
