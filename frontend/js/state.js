import { state } from './state.js';
import { API, GOOGLE_CLIENT_ID, apiFetch } from './api.js';

export const state = {
    token: localStorage.getItem('token') || null,
    username: localStorage.getItem('username') || null,
    isAdmin: false,
    _allProblems: [],
    _allSubs: [],
    _lbData: [],
    _lbSortKey: 'solved',
    _settingsData: null,
    _contestTimers: {},
    pollInterval: null,
    globalAbortController: new AbortController()
};

