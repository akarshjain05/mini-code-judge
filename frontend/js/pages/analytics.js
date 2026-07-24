// ── Analytics Page ──────────────────────────────────────────────────
// ── Analytics Dashboard ─────────────────────────────────────────────
async function loadAnalytics() {
  if (!token) { openAuthModal(); return; }
  try {
    const [subsRes, probsRes] = await Promise.all([
      fetch(`${API}/submissions?limit=200`, { headers: {} }),
      fetch(`${API}/problems`)
    ]);
    if (!subsRes.ok) throw new Error('Failed to load submissions');
    const subs = await subsRes.json();
    const problems = probsRes.ok ? await probsRes.json() : [];
    renderAnalytics(subs, problems);
  } catch(e) {
    console.error('Analytics error:', e);
    document.getElementById('analyticsStatsRow').innerHTML = '<p style="color:var(--warn)">⚠ Error loading analytics.</p>';
  }
}

// ── IST timezone helper (UTC+5:30) ─────────────────────────────────
const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;

function toIST(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return new Date(d.getTime() + IST_OFFSET_MS);
}

function toISTDateKey(dateStr) {
  const d = toIST(dateStr);
  if (!d) return null;
  // use UTC getters on the shifted date to get IST calendar date
  return `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}`;
}

function toISTHour(dateStr) {
  const d = toIST(dateStr);
  if (!d) return null;
  return d.getUTCHours();
}

function formatHour(h) {
  if (h === 0) return '12am';
  if (h === 12) return '12pm';
  return h < 12 ? h + 'am' : (h - 12) + 'pm';
}

function renderAnalytics(subs, problems = []) {
  if (!subs.length) {
    document.getElementById('analyticsStatsRow').innerHTML = '<p style="color:var(--muted)">No submissions yet. Solve some problems first!</p>';
    return;
  }

  const total = subs.length;
  const accepted = subs.filter(s => s.verdict === 'accepted').length;
  const accuracy = total ? Math.round((accepted / total) * 100) : 0;

  // ── Streak (in IST) ────────────────────────────────────────────────
  const acceptedDays = new Set(
    subs.filter(s => s.verdict === 'accepted').map(s => toISTDateKey(s.created_at)).filter(Boolean)
  );
  let streak = 0;
  const nowIST = toIST(new Date().toISOString());
  for (let i = 0; i < 365; i++) {
    const d = new Date(nowIST.getTime() - i * 86400000);
    const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}`;
    if (acceptedDays.has(key)) streak++;
    else if (i > 0) break;
  }

  document.getElementById('statTotal').textContent = total;
  document.getElementById('statAccepted').textContent = accepted;
  document.getElementById('statAccuracy').textContent = accuracy + '%';
  document.getElementById('statStreak').textContent = streak + (streak === 1 ? ' day' : ' days');

  // ── Difficulty breakdown ───────────────────────────────────────────
  if (problems.length) {
    // Map problem id -> difficulty
    const probMap = {};
    const diffTotals = { easy: 0, medium: 0, hard: 0 };
    problems.forEach(p => {
      probMap[p.id] = (p.difficulty || '').toLowerCase();
      const d = (p.difficulty || '').toLowerCase();
      if (diffTotals[d] !== undefined) diffTotals[d]++;
    });
    // Unique problems solved per difficulty (only accepted, unique problem_ids)
    const solvedByDiff = { easy: new Set(), medium: new Set(), hard: new Set() };
    subs.filter(s => s.verdict === 'accepted').forEach(s => {
      const diff = probMap[s.problem_id];
      if (diff && solvedByDiff[diff]) solvedByDiff[diff].add(s.problem_id);
    });
    const totalSolved = solvedByDiff.easy.size + solvedByDiff.medium.size + solvedByDiff.hard.size;
    const totalProbs  = problems.length;
    document.getElementById('diffEasySolved').textContent   = solvedByDiff.easy.size;
    document.getElementById('diffMediumSolved').textContent = solvedByDiff.medium.size;
    document.getElementById('diffHardSolved').textContent   = solvedByDiff.hard.size;
    document.getElementById('diffEasyTotal').textContent    = `of ${diffTotals.easy} problem${diffTotals.easy !== 1 ? 's' : ''}`;
    document.getElementById('diffMediumTotal').textContent  = `of ${diffTotals.medium} problem${diffTotals.medium !== 1 ? 's' : ''}`;
    document.getElementById('diffHardTotal').textContent    = `of ${diffTotals.hard} problem${diffTotals.hard !== 1 ? 's' : ''}`;
    document.getElementById('totalSolvedLine').innerHTML    = `<strong>${totalSolved}</strong> unique problems solved out of <strong>${totalProbs}</strong> available`;
  }

  // ── Language accuracy ──────────────────────────────────────────────
  const langStats = {};
  subs.forEach(s => {
    const l = s.language || 'unknown';
    if (!langStats[l]) langStats[l] = { total: 0, accepted: 0 };
    langStats[l].total++;
    if (s.verdict === 'accepted') langStats[l].accepted++;
  });
  
  const lColors = { python: '#f59e0b', cpp: '#007bff', nodejs: '#10b981', java: '#ef4444', go: '#0ea5e9' };
  document.getElementById('langAccuracyChart').innerHTML = Object.entries(langStats).map(([l, st]) => {
    const acc = Math.round((st.accepted / st.total) * 100);
    const color = lColors[l] || '#6b7280';
    return `
      <div style="margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:700;margin-bottom:6px">
          <span style="text-transform:uppercase">${l}</span>
          <span style="color:var(--muted)">${st.accepted}/${st.total} (${acc}%)</span>
        </div>
        <div style="height:6px;background:var(--surface2);border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${acc}%;background:${color};border-radius:3px"></div>
        </div>
      </div>`;
  }).join('');

  // ── Verdict breakdown (Donut Chart) ──────────────────────────────────────────────
  const verdicts = {};
  subs.forEach(s => {
    const v = s.verdict || s.status || 'unknown';
    verdicts[v] = (verdicts[v] || 0) + 1;
  });
  const vColors = { accepted: '#4ade80', wrong_answer: '#ef4444', time_limit_exceeded: '#f59e0b', compile_error: '#8b5cf6', runtime_error: '#f97316', pending: '#6b7280' };
  const vLabels = { accepted: 'Accepted', wrong_answer: 'Wrong Answer', time_limit_exceeded: 'Time Limit', compile_error: 'Compile Error', runtime_error: 'Runtime Error', pending: 'Pending' };
  
  const totalVerdicts = Object.values(verdicts).reduce((a,b)=>a+b, 0);
  let conicStops = [];
  let currentAngle = 0;
  
  const legendHtml = Object.entries(verdicts).map(([v, count]) => {
    const pct = Math.round((count / totalVerdicts) * 100);
    const color = vColors[v] || '#6b7280';
    const angle = (count / totalVerdicts) * 360;
    conicStops.push(`${color} ${currentAngle}deg ${currentAngle + angle}deg`);
    currentAngle += angle;
    
    return `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:12px;">
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:12px;height:12px;border-radius:3px;background:${color}"></div>
          <span style="color:var(--text);font-weight:500">${vLabels[v] || v}</span>
        </div>
        <span style="color:var(--muted)">${count} (${pct}%)</span>
      </div>`;
  }).join('');
  
  const gradient = conicStops.length ? `conic-gradient(${conicStops.join(', ')})` : 'none';
  
  document.getElementById('verdictBreakdown').innerHTML = `
    <div style="display:flex;align-items:center;gap:32px;margin-top:14px;padding-left:10px;">
      <div style="width:130px;height:130px;border-radius:50%;background:${gradient};flex-shrink:0;display:flex;align-items:center;justify-content:center;">
        <div style="width:80px;height:80px;border-radius:50%;background:var(--surface);"></div>
      </div>
      <div style="flex:1">
        ${legendHtml}
      </div>
    </div>
  `;

  // ── Activity Heatmap (last 12 weeks, IST dates) ────────────────────
  const activityMap = {};
  subs.forEach(s => {
    const key = toISTDateKey(s.created_at);
    if (!key) return;
    activityMap[key] = (activityMap[key] || 0) + 1;
  });

  const weeks = 12;
  const nowISTMidnight = new Date(nowIST);
  nowISTMidnight.setUTCHours(0,0,0,0);
  const startDate = new Date(nowISTMidnight.getTime() - (weeks * 7 - 1) * 86400000);

  const dayLabels = ['Sun','','Tue','','Thu','','Sat'];
  let heatmapHTML = '<div style="display:flex;gap:4px">';
  heatmapHTML += '<div style="display:flex;flex-direction:column;gap:2px;padding-top:18px">';
  dayLabels.forEach(lbl => {
    heatmapHTML += `<div style="height:12px;font-size:9px;color:var(--muted);line-height:12px">${lbl}</div>`;
  });
  heatmapHTML += '</div>';

  for (let w = 0; w < weeks; w++) {
    heatmapHTML += '<div style="display:flex;flex-direction:column;gap:2px">';
    const weekStart = new Date(startDate.getTime() + w * 7 * 86400000);
    const monthLabel = w % 4 === 0 ? weekStart.toLocaleDateString('en', {month:'short'}) : '';
    heatmapHTML += `<div style="height:14px;font-size:9px;color:var(--muted)">${monthLabel}</div>`;
    for (let dd = 0; dd < 7; dd++) {
      const date = new Date(startDate.getTime() + (w * 7 + dd) * 86400000);
      const key = `${date.getUTCFullYear()}-${date.getUTCMonth()}-${date.getUTCDate()}`;
      const count = activityMap[key] || 0;
      const color = count === 0 ? 'var(--surface2)' : count === 1 ? '#1e4023' : count <= 3 ? '#2d6a31' : count <= 5 ? '#3d8b42' : '#4ade80';
      const dateStr = date.toLocaleDateString('en-IN', {day:'numeric',month:'short',timeZone:'UTC'});
      const title = count ? `${count} submission${count>1?'s':''} on ${dateStr}` : dateStr;
      heatmapHTML += `<div title="${title}" style="width:12px;height:12px;border-radius:2px;background:${color};cursor:default"></div>`;
    }
    heatmapHTML += '</div>';
  }
  heatmapHTML += '</div>';
  document.getElementById('activityHeatmap').innerHTML = heatmapHTML;

  // ── Best Time to Code (IST hours) ─────────────────────────────────
  const hourCounts = Array(24).fill(0);
  subs.forEach(s => {
    const h = toISTHour(s.created_at);
    if (h === null) return;
    hourCounts[h]++;
  });
  const maxCount = Math.max(...hourCounts);
  const peakHour = maxCount > 0 ? hourCounts.indexOf(maxCount) : null;
  const timeHTML = `
    <div style="display:flex;gap:3px;align-items:flex-end;height:60px">
      ${hourCounts.map((c, h) => {
        const pct = maxCount > 0 ? Math.round((c / maxCount) * 100) : 0;
        const color = pct > 70 ? '#4ade80' : pct > 40 ? '#3d8b42' : pct > 10 ? '#2d6a31' : 'var(--surface2)';
        const label = h % 6 === 0 ? formatHour(h) : '';
        return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
          <div title="${c} submission${c!==1?'s':''} at ${formatHour(h)} IST" style="width:100%;height:${Math.max(pct*0.5,2)}px;background:${color};border-radius:2px 2px 0 0"></div>
          <div style="font-size:9px;color:var(--muted);white-space:nowrap">${label}</div>
        </div>`;
      }).join('')}
    </div>
    <div style="margin-top:8px;font-size:12px;color:var(--muted)">
      ${peakHour !== null
        ? `Peak time (IST): <strong style="color:var(--text)">${formatHour(peakHour)} – ${formatHour((peakHour+1)%24)}</strong>`
        : `<span>No submissions yet to show peak time</span>`}
    </div>`;
  document.getElementById('timeHeatmap').innerHTML = timeHTML;
}
