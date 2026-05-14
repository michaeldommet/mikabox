import { useState, useEffect } from 'react';
import { useDevice } from '../contexts/DeviceContext';
import { api } from '../api/client';

export default function Settings() {
  const { devices } = useDevice();
  const [serverHealth, setServerHealth] = useState(null);
  const [darkMode, setDarkMode] = useState(
    document.documentElement.getAttribute('data-theme') === 'dark'
  );

  useEffect(() => {
    api.health().then(setServerHealth).catch(() => setServerHealth({ status: 'error' }));
  }, []);

  const toggleDarkMode = () => {
    const next = !darkMode;
    setDarkMode(next);
    document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light');
    localStorage.setItem('mikabox_theme', next ? 'dark' : 'light');
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Device and app configuration</p>
      </div>

      {/* Server Status */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">🖥️ Server Status</span>
          <span className={`badge ${serverHealth?.status === 'ok' ? 'badge-success' : 'badge-error'}`}>
            {serverHealth?.status === 'ok' ? 'Online' : 'Offline'}
          </span>
        </div>
        {serverHealth && (
          <div className="info-rows">
            <div className="info-row">
              <span className="info-label">Version</span>
              <span style={{ fontSize: '0.875rem' }}>{serverHealth.version || 'Unknown'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">AI Engine</span>
              <span className={`badge ${serverHealth.ai_ready ? 'badge-success' : 'badge-warning'}`}>
                {serverHealth.ai_ready ? 'Ready' : 'Not Loaded'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Paired Devices */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">📱 Paired Devices</span>
        </div>
        {devices.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
            No devices paired yet.
          </p>
        ) : (
          <div className="info-rows">
            {devices.map(d => (
              <div key={d.id} className="info-row">
                <div className="flex items-center gap-sm">
                  <span>🎵</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{d.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{d.device_id}</div>
                  </div>
                </div>
                <span className={`badge ${d.is_online ? 'badge-success' : 'badge-error'}`}>
                  {d.is_online ? 'Online' : 'Offline'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* App Settings */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">🎨 App Settings</span>
        </div>
        <div className="info-rows">
          <div className="info-row">
            <span className="info-label">Dark Mode</span>
            <label className="toggle">
              <input type="checkbox" checked={darkMode} onChange={toggleDarkMode} id="dark-mode-toggle" />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
      </div>

      {/* Privacy */}
      <div className="card mt-lg">
        <div className="card-header">
          <span className="card-title">🔒 Privacy & Data</span>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginBottom: 16 }}>
          All voice processing happens on your home server. No data is sent to external servers.
          Your children's data is stored locally and never shared.
        </p>
        <div className="flex gap-sm">
          <button className="btn btn-secondary">📋 Export My Data</button>
          <button className="btn btn-danger">🗑️ Delete All Data</button>
        </div>
      </div>

      <style>{`
        .info-rows { display: flex; flex-direction: column; gap: 4px; }
        .info-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 0;
          border-bottom: 1px solid var(--color-border-light);
        }
        .info-row:last-child { border-bottom: none; }
        .info-label {
          font-size: 0.8125rem;
          color: var(--color-text-muted);
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
