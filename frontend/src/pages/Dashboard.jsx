import { useState, useEffect } from 'react';
import { useDevice } from '../contexts/DeviceContext';
import { api } from '../api/client';

export default function Dashboard() {
  const { deviceState, sendCommand } = useDevice();
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    api.getUsageSummary().then(setUsage).catch(() => {});
  }, []);

  const dailyLimit = 120; // minutes
  const usagePercent = Math.min(100, (deviceState.usage_today_minutes / dailyLimit) * 100);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Your MikaBox at a glance</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <div className="card stat-card">
          <div className="card-icon" style={{ margin: '0 auto 12px', background: deviceState.connected ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' }}>
            {deviceState.connected ? '🟢' : '🔴'}
          </div>
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {deviceState.connected ? 'Online' : 'Offline'}
          </div>
          <div className="stat-label">Device Status</div>
        </div>

        <div className="card stat-card">
          <div className="card-icon" style={{ margin: '0 auto 12px' }}>🎧</div>
          <div className="stat-value">{Math.round(deviceState.usage_today_minutes)}m</div>
          <div className="stat-label">Listened Today</div>
        </div>

        <div className="card stat-card">
          <div className="card-icon" style={{ margin: '0 auto 12px' }}>⏳</div>
          <div className="stat-value">{Math.round(deviceState.remaining_minutes)}m</div>
          <div className="stat-label">Remaining</div>
        </div>

        <div className="card stat-card">
          <div className="card-icon" style={{ margin: '0 auto 12px' }}>🔊</div>
          <div className="stat-value">{deviceState.volume}%</div>
          <div className="stat-label">Volume</div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Now Playing */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Now Playing</span>
            <span className={`badge ${deviceState.state === 'playing' ? 'badge-success' : 'badge-primary'}`}>
              {deviceState.state}
            </span>
          </div>
          {deviceState.current_track ? (
            <div className="now-playing-info">
              <div className="now-playing-art">🎵</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                  {deviceState.current_track.name || 'Unknown'}
                </div>
                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', marginTop: 4 }}>
                  Track {deviceState.current_track.index + 1} of {deviceState.current_track.total_tracks}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '20px 0' }}>
              Nothing playing right now
            </div>
          )}
          <div className="quick-controls mt-md">
            <button className="btn btn-secondary btn-icon" onClick={() => sendCommand('skip_back')}>⏮</button>
            <button className="btn btn-primary btn-icon" style={{ width: 48, height: 48, fontSize: '1.25rem' }}
              onClick={() => sendCommand(deviceState.state === 'playing' ? 'pause' : 'resume')}>
              {deviceState.state === 'playing' ? '⏸' : '▶️'}
            </button>
            <button className="btn btn-secondary btn-icon" onClick={() => sendCommand('skip_forward')}>⏭</button>
            <button className="btn btn-secondary btn-icon" onClick={() => sendCommand('stop')}>⏹</button>
          </div>
        </div>

        {/* Usage Progress */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Daily Usage</span>
            <span className="badge badge-primary">{Math.round(usagePercent)}%</span>
          </div>
          <div className="usage-ring-container">
            <svg width="140" height="140" viewBox="0 0 140 140" className="usage-ring">
              <circle cx="70" cy="70" r="58" fill="none" stroke="var(--color-border)" strokeWidth="10" />
              <circle cx="70" cy="70" r="58" fill="none"
                stroke="url(#usage-gradient)" strokeWidth="10" strokeLinecap="round"
                strokeDasharray={`${usagePercent * 3.64} 364`}
                transform="rotate(-90 70 70)"
                style={{ transition: 'stroke-dasharray 0.6s ease' }}
              />
              <defs>
                <linearGradient id="usage-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--color-primary)" />
                  <stop offset="100%" stopColor="var(--color-accent)" />
                </linearGradient>
              </defs>
            </svg>
            <div className="usage-ring-text">
              <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.5rem' }}>
                {Math.round(deviceState.usage_today_minutes)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                of {dailyLimit} min
              </div>
            </div>
          </div>
          {usage && (
            <div className="flex justify-between mt-md" style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              <span>This week: {Math.round(usage.week_minutes || 0)}m</span>
              <span>This month: {Math.round(usage.month_minutes || 0)}m</span>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .now-playing-info {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 12px 0;
        }
        .now-playing-art {
          width: 56px;
          height: 56px;
          border-radius: var(--radius-md);
          background: linear-gradient(135deg, var(--color-primary-soft), rgba(249,112,102,0.08));
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
        }
        .quick-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
        }
        .usage-ring-container {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px 0;
        }
        .usage-ring-text {
          position: absolute;
          text-align: center;
        }
      `}</style>
    </div>
  );
}
