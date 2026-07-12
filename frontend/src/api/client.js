/**
 * API client for Task Manager backend.
 * Base URL is proxied through package.json "proxy" in dev,
 * or set via REACT_APP_API_URL environment variable.
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '/api';

// Dev-only header auth: matches backend SimpleAuthMiddleware.
// Persist the picked employer in localStorage so the user doesn't lose
// context on reload.
const STORAGE_KEY = 'task-manager.employerId';
export const getEmployerId = () => localStorage.getItem(STORAGE_KEY) || '1';
export const setEmployerId = (id) => {
  if (id) {
    localStorage.setItem(STORAGE_KEY, String(id));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
};

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
});

client.interceptors.request.use((config) => {
  config.headers['X-Employer-Id'] = getEmployerId();
  config.headers['X-User-Role'] = 'employer';
  return config;
});

// Normalize errors so callers can show a useful message.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'Unexpected error.';
    if (error.code === 'ECONNABORTED') {
      message = 'The server took too long to respond. Please try again.';
    } else if (error.response) {
      const { status, data } = error.response;
      if (status === 0 || status >= 500) {
        message = 'The server is unavailable. Please try again shortly.';
      } else if (status === 403) {
        message = 'You are not allowed to perform this action.';
      } else if (status === 404) {
        message = 'Not found.';
      } else if (status === 429) {
        message = 'Too many requests — slow down.';
      } else if (data && typeof data === 'object') {
        // DRF-style: { field: ["msg"] } or { detail: "msg" }
        if (data.detail) {
          message = data.detail;
        } else {
          const flat = Object.entries(data)
            .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`)
            .join('\n');
          message = flat || message;
        }
      }
    } else if (error.request) {
      message = 'Network error — check your connection and the backend.';
    }
    error.userMessage = message;
    return Promise.reject(error);
  }
);

// Pagination helper — DRF returns either {results, count, next, previous}
// or a bare array when pagination is disabled.
export const unwrapList = (data) => {
  if (Array.isArray(data)) return { results: data, count: data.length, next: null, previous: null };
  return {
    results: data?.results ?? [],
    count: data?.count ?? 0,
    next: data?.next ?? null,
    previous: data?.previous ?? null,
  };
};

export default client;

// API endpoints
export const workersApi = {
  list: (params) => client.get('/workers/', { params }),
  get: (id) => client.get(`/workers/${id}/`),
  create: (data) => client.post('/workers/', data),
  update: (id, data) => client.put(`/workers/${id}/`, data),
  delete: (id) => client.delete(`/workers/${id}/`),
};

export const employersApi = {
  list: (params) => client.get('/employers/', { params }),
  get: (id) => client.get(`/employers/${id}/`),
  workers: (id) => client.get(`/employers/${id}/workers/`),
  dashboard: (id) => client.get(`/employers/${id}/dashboard/`),
};

export const tasksApi = {
  list: (params) => client.get('/tasks/', { params }),
  get: (id) => client.get(`/tasks/${id}/`),
  create: (data) => client.post('/tasks/', data),
  update: (id, data) => client.put(`/tasks/${id}/`, data),
  patch: (id, data) => client.patch(`/tasks/${id}/`, data),
  delete: (id) => client.delete(`/tasks/${id}/`),
  complete: (id) => client.post(`/tasks/${id}/complete/`),
  transition: (id, status) => client.post(`/tasks/${id}/transition/`, { status }),
  stats: () => client.get('/tasks/stats/'),
};

export const notificationsApi = {
  list: (params) => client.get('/notifications/items/', { params }),
  unread: () => client.get('/notifications/items/unread/'),
  markRead: (id) => client.post(`/notifications/items/${id}/mark-read/`),
  markAllRead: () => client.post('/notifications/items/mark-all-read/'),
  preferences: () => client.get('/notifications/preferences/'),
  updatePreferences: (data) => client.post('/notifications/preferences/', data),
};

export const translationApi = {
  translate: (text, target, source) =>
    client.post('/translation/translate/', { text, target, source }),
};

export const healthApi = {
  check: () => client.get('/health/'),
};
