// ── Config & State ─────────────────────────────────────────────────
const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://mini-code-judge.onrender.com';
const GOOGLE_CLIENT_ID = '195071714890-cqr22mhg2cvfc1ttad54j8qgdqc3ee24.apps.googleusercontent.com';

let token    = localStorage.getItem('jwt') || null;
let username = localStorage.getItem('username') || null;
let isAdmin  = false;
let _allProblems   = [];
let _allSubs       = [];
let _lbData        = [];
let _lbSortKey     = 'solved';
let _settingsData  = null;
let _contestTimers = {};
let pollInterval = null;

// #region agent log
function _dbgLog(location, message, data, hypothesisId) {
  fetch('http://127.0.0.1:7611/ingest/50436459-408a-4c35-b419-fa3171b85e31',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'63f610'},body:JSON.stringify({sessionId:'63f610',location,message,data,hypothesisId,timestamp:Date.now()})}).catch(()=>{});
}
// #endregion

/** Fetch with retries — handles Render cold-start / transient network failures. */
async function apiFetch(url, options = {}, retriesLeft = 3) {
  let lastErr;
  for (let attempt = 0; attempt <= retriesLeft; attempt++) {
    try {
      const res = await fetch(url, options);
      // #region agent log
      _dbgLog('config.js:apiFetch', 'fetch response', { url, status: res.status, ok: res.ok, attempt }, 'A');
      // #endregion
      return res;
    } catch (e) {
      lastErr = e;
      // #region agent log
      _dbgLog('config.js:apiFetch', 'fetch threw', { url, attempt, err: String(e) }, 'A');
      // #endregion
      if (attempt < retriesLeft) await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }
  throw lastErr;
}