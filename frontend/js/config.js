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

/** Fetch with retries — handles Render cold-start / transient network failures. */
async function apiFetch(url, options = {}, retriesLeft = 3) {
  let lastErr;
  for (let attempt = 0; attempt <= retriesLeft; attempt++) {
    try {
      const res = await fetch(url, options);
      return res;
    } catch (e) {
      lastErr = e;
      if (attempt < retriesLeft) await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }
  throw lastErr;
}