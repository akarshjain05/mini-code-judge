// ── Submit / Code Editor ────────────────────────────────────────────
// ── Submit ─────────────────────────────────────────────────────────
async function submitCode() {
  if (!token) { openAuthModal(); return; }
  if (!currentProblem) { alert('No problem selected'); return; }
  const code = document.getElementById('codeInput').value;
  const lang = document.getElementById('langSelect').value;

  const vbox = document.getElementById('verdictBox');
  const vtitle = document.getElementById('verdictTitle');
  const vsub = document.getElementById('verdictSub');
  const vmeta = document.getElementById('verdictMeta');
  const verr = document.getElementById('verdictError');
  const log = document.getElementById('submitLog');
  const logText = document.getElementById('submitLogText');

  vbox.classList.add('show');
  vbox.style.borderColor = 'var(--border)';
  vtitle.className = 'verdict-title verdict-pending';
  log.style.display = 'none';
  logText.textContent = '';
  vtitle.innerHTML = '<span class="spinner"></span> &nbsp;Judging…';
  vsub.textContent = ''; vmeta.textContent = ''; verr.style.display = 'none';
  log.style.display = 'none';
  logText.textContent = '→ Sending code to judge…\n';

  try {
    const res = await fetch(`${API}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ problem_id: currentProblem.id, language: lang, code }),
    });
    const sub = await res.json();
    if (!res.ok) { vtitle.textContent = '✗ Error'; vsub.textContent = sub.detail; vtitle.className = 'verdict-title verdict-wrong_answer'; return; }

    vtitle.innerHTML = '<span class="spinner"></span> &nbsp;Judging…';

    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(() => pollVerdict(sub.id, logText, vtitle, vsub, vmeta, verr, vbox), 1500);
  } catch(e) { vtitle.textContent = '⚠ Cannot reach API'; vtitle.className = 'verdict-title verdict-wrong_answer'; }
}

async function pollVerdict(id, logText, vtitle, vsub, vmeta, verr, vbox) {
  try {
    const res = await fetch(`${API}/submissions/${id}`, { headers: { 'Authorization': `Bearer ${token}` } });
    const sub = await res.json();
    if (sub.status === 'pending' || sub.status === 'running') {
      return;
    }
    clearInterval(pollInterval);

    const icons = { accepted:'✓', wrong_answer:'✗', time_limit_exceeded:'⏱', compile_error:'⚙', runtime_error:'⚠', no_test_cases:'?' };
    vtitle.className = `verdict-title verdict-${sub.verdict || sub.status}`;
    vtitle.textContent = `${icons[sub.verdict] || '?'}  ${formatVerdict(sub.verdict || sub.status)}`;
    vsub.textContent = sub.verdict === 'accepted' ? 'All test cases passed!' : 'Check your logic and try again.';
    if (sub.runtime_ms) vmeta.innerHTML = `<span>⚡ ${sub.runtime_ms.toFixed(1)} ms</span><span>🧠 ${sub.memory_kb || '—'} KB</span>`;
    if (sub.error_output && sub.error_output !== 'SAMPLE_ONLY') { verr.textContent = sub.error_output; verr.style.display = 'block'; }
    // Show AI Review button after verdict
    const aiBtn = document.getElementById('aiReviewBtn');
    if (aiBtn) {
      aiBtn.style.display = 'block';
      aiBtn.dataset.submissionId = sub.id;
      aiBtn.dataset.verdict = sub.verdict || sub.status;
      aiBtn.dataset.code = '';  // will fetch from sub
      document.getElementById('aiReviewPanel').style.display = 'none';
    }
    window._lastSubId = sub.id;
  } catch(e) { clearInterval(pollInterval); }
}

function formatVerdict(v) {
  const map = { accepted:'Accepted', wrong_answer:'Wrong Answer', time_limit_exceeded:'Time Limit Exceeded', compile_error:'Compile Error', runtime_error:'Runtime Error', no_test_cases:'No Test Cases', queue_error:'Queue Error' };
  return map[v] || v;
}
