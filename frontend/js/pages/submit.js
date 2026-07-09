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

  // Reset any AI review state left over from a previous submission of this
  // problem — a new submission needs a fresh review, not a stale button.
  const aiBtnReset = document.getElementById('aiReviewBtn');
  if (aiBtnReset) {
    aiBtnReset.style.display = 'none';
    aiBtnReset.disabled = false;
    aiBtnReset.textContent = '🤖 Get AI Code Review';
    delete aiBtnReset.dataset.submissionId;
    delete aiBtnReset.dataset.verdict;
  }
  const aiPanelReset = document.getElementById('aiReviewPanel');
  if (aiPanelReset) aiPanelReset.style.display = 'none';

  try {
    const res = await apiFetch(`${API}/submissions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem_id: currentProblem.id, language: lang, code }),
    });
    let sub;
    try {
      sub = await res.json();
    } catch(err) {
      sub = { detail: `Status ${res.status}: Invalid JSON response` };
    }
    if (!res.ok) { vtitle.textContent = '✗ Error'; vsub.textContent = sub.detail || 'Submit failed'; vtitle.className = 'verdict-title verdict-wrong_answer'; return; }
    if (!sub.id) { vtitle.textContent = '✗ Error'; vsub.textContent = 'Invalid server response (missing submission id)'; vtitle.className = 'verdict-title verdict-wrong_answer'; return; }

    vtitle.innerHTML = '<span class="spinner"></span> &nbsp;Judging…';

    if (pollInterval) clearInterval(pollInterval);
    window._pollStartedAt = Date.now();
    window._pollFailCount = 0;
    pollInterval = setInterval(() => pollVerdict(sub.id, logText, vtitle, vsub, vmeta, verr, vbox), 1500);
  } catch(e) {
    vtitle.textContent = '⚠ Cannot reach API';
    vsub.textContent = 'Server may be waking up — try again in a moment.';
    vtitle.className = 'verdict-title verdict-wrong_answer';
  }
}

async function pollVerdict(id, logText, vtitle, vsub, vmeta, verr, vbox) {
  if (window._pollStartedAt && Date.now() - window._pollStartedAt > 180000) {
    clearInterval(pollInterval);
    vtitle.className = 'verdict-title verdict-wrong_answer';
    vtitle.textContent = '⏱ Judging timed out';
    vsub.textContent = 'The server took too long — try submitting again.';
    return;
  }
  try {
    const res = await fetch(`${API}/submissions/${id}`, { headers: {} });
    if (!res.ok) {
      window._pollFailCount = (window._pollFailCount || 0) + 1;
      if (window._pollFailCount >= 5) {
        clearInterval(pollInterval);
        vtitle.className = 'verdict-title verdict-wrong_answer';
        vtitle.textContent = '⚠ Cannot reach API';
        vsub.textContent = `Poll failed (HTTP ${res.status}) — refresh and try again.`;
      }
      return;
    }
    window._pollFailCount = 0;
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
    const aiBtn = document.getElementById('aiReviewBtn');
    if (aiBtn) {
      aiBtn.style.display = 'block';
      aiBtn.dataset.submissionId = sub.id;
      aiBtn.dataset.verdict = sub.verdict || sub.status;
      aiBtn.dataset.code = '';
      document.getElementById('aiReviewPanel').style.display = 'none';
    }
    window._lastSubId = sub.id;
  } catch(e) {
    window._pollFailCount = (window._pollFailCount || 0) + 1;
    if (window._pollFailCount >= 5) {
      clearInterval(pollInterval);
      vtitle.className = 'verdict-title verdict-wrong_answer';
      vtitle.textContent = '⚠ Cannot reach API';
      vsub.textContent = 'Lost connection while waiting for verdict — try again.';
    }
  }
}

function formatVerdict(v) {
  const map = { accepted:'Accepted', wrong_answer:'Wrong Answer', time_limit_exceeded:'Time Limit Exceeded', compile_error:'Compile Error', runtime_error:'Runtime Error', no_test_cases:'No Test Cases', queue_error:'Queue Error', judge_error:'Judge Error', error:'Error' };
  return map[v] || v;
}
