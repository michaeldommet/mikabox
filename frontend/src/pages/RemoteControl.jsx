import { useDevice } from '../contexts/DeviceContext';

export default function RemoteControl() {
  const { deviceState, sendCommand } = useDevice();

  const track = deviceState.current_track;
  const isPlaying = deviceState.state === 'playing';
  const progressPercent = track && track.duration_ms > 0
    ? (track.position_ms / track.duration_ms) * 100
    : 0;

  const formatTime = (ms) => {
    if (!ms || ms < 0) return '0:00';
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Remote Control</h1>
        <p>Control your MikaBox in real-time</p>
      </div>

      <div className="remote-container">
        {/* Album Art / Now Playing */}
        <div className="card remote-now-playing">
          <div className="remote-art">
            <div className="remote-art-inner">
              {isPlaying ? '🎵' : '💤'}
            </div>
            {isPlaying && <div className="remote-art-ring" />}
          </div>

          <div className="remote-track-info">
            <h2>{track?.name || 'Nothing Playing'}</h2>
            {track && (
              <p>Track {track.index + 1} of {track.total_tracks}</p>
            )}
          </div>

          {/* Progress bar */}
          <div className="remote-progress">
            <span className="remote-time">{formatTime(track?.position_ms)}</span>
            <div className="remote-progress-bar">
              <div className="remote-progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>
            <span className="remote-time">{formatTime(track?.duration_ms)}</span>
          </div>

          {/* Playback Controls */}
          <div className="remote-controls">
            <button className="btn btn-secondary btn-icon" onClick={() => sendCommand('skip_back')} title="Previous">
              ⏮
            </button>
            <button
              className="btn btn-primary remote-play-btn"
              onClick={() => sendCommand(isPlaying ? 'pause' : 'resume')}
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? '⏸' : '▶️'}
            </button>
            <button className="btn btn-secondary btn-icon" onClick={() => sendCommand('skip_forward')} title="Next">
              ⏭
            </button>
          </div>

          {/* Volume */}
          <div className="remote-volume">
            <span className="remote-volume-icon">🔈</span>
            <input
              type="range"
              className="slider"
              min="0"
              max="100"
              value={deviceState.volume}
              onChange={e => sendCommand('set_volume', { level: parseInt(e.target.value) })}
              id="remote-volume-slider"
            />
            <span className="remote-volume-label">{deviceState.volume}%</span>
          </div>

          {/* Quick Actions */}
          <div className="remote-actions">
            <button className="btn btn-secondary" onClick={() => sendCommand('stop')}>
              ⏹ Stop
            </button>
          </div>
        </div>

        {/* Device Info */}
        <div className="card remote-info">
          <div className="card-header">
            <span className="card-title">Device Info</span>
          </div>
          <div className="info-rows">
            <div className="info-row">
              <span className="info-label">Status</span>
              <span className={`badge ${deviceState.connected ? 'badge-success' : 'badge-error'}`}>
                {deviceState.connected ? 'Connected' : 'Offline'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">State</span>
              <span className="badge badge-primary">{deviceState.state}</span>
            </div>
            <div className="info-row">
              <span className="info-label">NFC Tag</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                {deviceState.nfc_tag || 'None'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Active Profile</span>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                {deviceState.profile_id}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Today's Usage</span>
              <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                {Math.round(deviceState.usage_today_minutes)} min
              </span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .remote-container {
          display: grid;
          grid-template-columns: 1fr 320px;
          gap: 24px;
        }
        @media (max-width: 900px) {
          .remote-container { grid-template-columns: 1fr; }
        }
        .remote-now-playing {
          text-align: center;
          padding: 40px 32px;
        }
        .remote-art {
          position: relative;
          width: 160px;
          height: 160px;
          margin: 0 auto 24px;
        }
        .remote-art-inner {
          width: 100%;
          height: 100%;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 4rem;
          box-shadow: 0 12px 40px rgba(79, 70, 229, 0.25);
        }
        .remote-art-ring {
          position: absolute;
          inset: -8px;
          border-radius: 50%;
          border: 2px solid var(--color-primary-light);
          opacity: 0.4;
          animation: pulse-soft 2s ease-in-out infinite;
        }
        .remote-track-info h2 {
          font-family: var(--font-heading);
          font-size: 1.5rem;
          margin-bottom: 4px;
        }
        .remote-track-info p {
          color: var(--color-text-secondary);
          font-size: 0.875rem;
        }
        .remote-progress {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 24px 0;
        }
        .remote-time {
          font-size: 0.75rem;
          color: var(--color-text-muted);
          font-variant-numeric: tabular-nums;
          min-width: 36px;
        }
        .remote-progress-bar {
          flex: 1;
          height: 4px;
          background: var(--color-border);
          border-radius: 2px;
          overflow: hidden;
        }
        .remote-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
          border-radius: 2px;
          transition: width 0.3s linear;
        }
        .remote-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          margin-bottom: 24px;
        }
        .remote-play-btn {
          width: 64px !important;
          height: 64px !important;
          border-radius: 50% !important;
          font-size: 1.5rem !important;
          padding: 0 !important;
        }
        .remote-volume {
          display: flex;
          align-items: center;
          gap: 12px;
          max-width: 360px;
          margin: 0 auto 20px;
        }
        .remote-volume-icon { font-size: 1.25rem; }
        .remote-volume-label {
          font-size: 0.8125rem;
          font-weight: 600;
          color: var(--color-text-secondary);
          min-width: 36px;
          text-align: right;
        }
        .remote-actions {
          display: flex;
          justify-content: center;
          gap: 12px;
        }
        .info-rows { display: flex; flex-direction: column; gap: 12px; }
        .info-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
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
