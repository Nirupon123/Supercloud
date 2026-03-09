// ============================================================
// src/services/api.js
//
// CLOUD/AIOPS ERROR IN THIS FILE:
//
// [ERROR-13] NO RETRY ON NETWORK FAILURE:
//   In cloud environments, transient network failures (DNS glitches,
//   pod restarts, load balancer churn) are common. A single failed
//   request with no retry causes user-visible errors that a simple
//   automatic retry would have resolved.
//   AIOps detection: high rate of short-lived client errors correlated
//   with infra events (pod restarts, cert rotations, scaling events).
//
// [ERROR-14] NO REQUEST TIMEOUT ON CLIENT SIDE:
//   If the backend is slow (e.g., event loop blocked by CPU spike),
//   the frontend waits indefinitely with no timeout.
//   Users see a permanently spinning UI. AIOps detects p99 request
//   duration anomaly correlated with backend CPU spike.
// ============================================================

import axios from 'axios';

// Base URL reads from environment variable — correct cloud-native pattern.
// In production this would be the service DNS name.
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  // [ERROR-14] No timeout set — requests hang indefinitely if server is unresponsive
  // Should be: timeout: 10000  (10 seconds)
});

// Attach JWT token from localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// [ERROR-13] No retry interceptor.
// On 503, 429, or network errors, the request simply fails immediately.
// A cloud-resilient client should retry with exponential backoff.
// Axios itself has no built-in retry — needs axios-retry or similar.
// Example of what SHOULD be here:
//   axiosRetry(api, { retries: 3, retryDelay: axiosRetry.exponentialDelay });
// (intentionally NOT implemented)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log error but no retry — error is immediately surfaced to the component
    if (error.response) {
      console.error(`API Error ${error.response.status}: ${error.response.data?.message}`);
    } else if (error.request) {
      // [ERROR-13] Network error with no retry — one blip = user-visible failure
      console.error('Network error — no retry attempted');
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
};

export const productAPI = {
  getAll: (params) => api.get('/products', { params }),
  getById: (id) => api.get(`/products/${id}`),
  create: (data) => api.post('/products', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
};

export default api;
