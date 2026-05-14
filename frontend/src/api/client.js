/**
 * MikaBox API Client
 * 
 * Centralized HTTP + WebSocket client with JWT auth interceptors.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace('http', 'ws');

// ── Token Management ─────────────────────────────────────────────

let accessToken = localStorage.getItem('mikabox_token');
let refreshToken = localStorage.getItem('mikabox_refresh');

export function setTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('mikabox_token', access);
  localStorage.setItem('mikabox_refresh', refresh);
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('mikabox_token');
  localStorage.removeItem('mikabox_refresh');
}

export function getAccessToken() {
  return accessToken;
}

// ── HTTP Client ──────────────────────────────────────────────────

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Token expired — try refresh
  if (response.status === 401 && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      return fetch(url, { ...options, headers });
    }
  }

  return response;
}

async function refreshAccessToken() {
  try {
    const resp = await fetch(`${API_BASE}/api/auth/refresh?refresh_token=${refreshToken}`, {
      method: 'POST',
    });
    if (resp.ok) {
      const data = await resp.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    }
  } catch (e) {
    console.error('Token refresh failed:', e);
  }
  clearTokens();
  return false;
}

// ── API Methods ──────────────────────────────────────────────────

export const api = {
  // Auth
  async register(email, password, displayName) {
    const resp = await request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
    return resp.json();
  },

  async login(email, password) {
    const resp = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    return resp.json();
  },

  async getMe() {
    const resp = await request('/api/auth/me');
    return resp.json();
  },

  // Profiles
  async getProfiles() {
    const resp = await request('/api/profiles/');
    return resp.json();
  },

  async createProfile(data) {
    const resp = await request('/api/profiles/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return resp.json();
  },

  async updateProfile(id, data) {
    const resp = await request(`/api/profiles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return resp.json();
  },

  async deleteProfile(id) {
    return request(`/api/profiles/${id}`, { method: 'DELETE' });
  },

  // Devices
  async getDevices() {
    const resp = await request('/api/devices/');
    return resp.json();
  },

  async pairDevice(deviceId, name) {
    const resp = await request('/api/devices/pair', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, name }),
    });
    return resp.json();
  },

  // Content
  async getContent(params = {}) {
    const query = new URLSearchParams(params).toString();
    const resp = await request(`/api/content/?${query}`);
    return resp.json();
  },

  async getContentById(id) {
    const resp = await request(`/api/content/${id}`);
    return resp.json();
  },

  async uploadContent(formData) {
    // We don't use the default request function because it sets Content-Type to application/json
    const url = `${API_BASE}/api/content/upload`;
    const headers = {};
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload failed: ${errorText}`);
    }

    return response.json();
  },

  // Controls
  async sendCommand(command, payload = {}) {
    const resp = await request('/api/controls/send', {
      method: 'POST',
      body: JSON.stringify({ command, payload }),
    });
    return resp.json();
  },

  async getParentalRules() {
    const resp = await request('/api/controls/rules');
    return resp.json();
  },

  async updateParentalRules(rules) {
    const resp = await request('/api/controls/rules', {
      method: 'PUT',
      body: JSON.stringify(rules),
    });
    return resp.json();
  },

  // Usage
  async getUsageSummary(profileId) {
    const query = profileId ? `?profile_id=${profileId}` : '';
    const resp = await request(`/api/usage/summary${query}`);
    return resp.json();
  },

  async getUsageHistory(profileId, limit = 50) {
    const params = new URLSearchParams({ limit });
    if (profileId) params.set('profile_id', profileId);
    const resp = await request(`/api/usage/history?${params}`);
    return resp.json();
  },

  async getSearchHistory(profileId, limit = 50) {
    const params = new URLSearchParams({ limit });
    if (profileId) params.set('profile_id', profileId);
    const resp = await request(`/api/usage/searches?${params}`);
    return resp.json();
  },

  async clearSearchHistory(profileId) {
    const query = profileId ? `?profile_id=${profileId}` : '';
    const resp = await request(`/api/usage/searches${query}`, { method: 'DELETE' });
    return resp.json();
  },

  // Memory
  async getMemoryFacts(profileId) {
    const query = profileId ? `?profile_id=${profileId}` : '';
    const resp = await request(`/api/memory/${query}`);
    return resp.json();
  },

  async deleteMemoryFact(factId) {
    return request(`/api/memory/${factId}`, { method: 'DELETE' });
  },

  // Health
  async health() {
    const resp = await fetch(`${API_BASE}/api/health`);
    return resp.json();
  },
};

// ── WebSocket ────────────────────────────────────────────────────

export function createDeviceWebSocket(deviceId, onMessage) {
  const url = `${WS_BASE}/ws/app?device_id=${deviceId}`;
  let ws = null;
  let reconnectTimer = null;
  let reconnectDelay = 2000;

  function connect() {
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('[WS] Connected to device:', deviceId);
      reconnectDelay = 2000;
      onMessage({ type: 'connection', data: { connected: true } });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
      } catch (e) {
        console.warn('[WS] Invalid message:', event.data);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected. Reconnecting in', reconnectDelay, 'ms...');
      onMessage({ type: 'connection', data: { connected: false } });
      reconnectTimer = setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }

  function send(command, payload = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command, payload }));
    }
  }

  function disconnect() {
    clearTimeout(reconnectTimer);
    if (ws) ws.close();
  }

  connect();

  return { send, disconnect };
}
