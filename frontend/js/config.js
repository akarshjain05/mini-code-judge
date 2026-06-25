// ── Config & State ─────────────────────────────────────────────────
const API = 'https://mini-code-judge.onrender.com';
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