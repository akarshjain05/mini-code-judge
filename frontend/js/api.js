import { state } from './state.js';
import { API, GOOGLE_CLIENT_ID, apiFetch } from './api.js';

import { state } from './state.js';

export const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://mini-code-judge.onrender.com';

export const GOOGLE_CLIENT_ID = '195071714890-cqr22mhg2cvfc1ttad54j8qgdqc3ee24.apps.googleusercontent.com';

export async function apiFetch(url, options = {}, retriesLeft = 3) {
  options.credentials = 'include';
  options.headers = options.headers || {};
  if (state.token) {
    options.headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {
    options.headers['X-Requested-With'] = 'XMLHttpRequest';
  }
  if (!options.signal && (!options.method || options.method.toUpperCase() === 'GET')) {
    options.signal = state.globalAbortController.signal;
  }

  let lastErr;
  for (let attempt = 0; attempt <= retriesLeft; attempt++) {
    try {
      const res = await apiFetch(url, options);
      return res;
    } catch (e) {
      if (e.name === 'AbortError') throw e;
      lastErr = e;
      if (attempt < retriesLeft) await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }
  }
  throw lastErr;
}

window.apiFetch = apiFetch;
