import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useDevice } from '../contexts/DeviceContext';

const navItems = [
  { path: '/', icon: '📊', label: 'Dashboard' },
  { path: '/library', icon: '📚', label: 'Library' },
  { path: '/remote', icon: '🎮', label: 'Remote Control' },
  { path: '/controls', icon: '🛡️', label: 'Parental Controls' },
  { path: '/profiles', icon: '👶', label: 'Profiles' },
  { path: '/settings', icon: '⚙️', label: 'Settings' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  const { deviceState } = useDevice();
  const location = useLocation();

  return (
    <>
      {/* Mobile header */}
      <header className="mobile-header">
        <button className="mobile-menu-btn" onClick={() => setMobileOpen(!mobileOpen)}>
          ☰
        </button>
        <span className="mobile-title">🎵 MikaBox</span>
        <div className="mobile-status">
          <span className={`status-dot ${deviceState.connected ? 'online' : 'offline'}`} />
        </div>
      </header>

      {/* Overlay */}
      {mobileOpen && <div className="sidebar-overlay" onClick={() => setMobileOpen(false)} />}

      {/* Sidebar */}
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-icon">🎵</div>
          {!collapsed && <span className="logo-text">MikaBox</span>}
        </div>

        {/* Device Status */}
        {!collapsed && (
          <div className="sidebar-device-status">
            <div className={`device-indicator ${deviceState.connected ? 'online' : 'offline'}`}>
              <span className="status-dot" />
              <span>{deviceState.connected ? 'Connected' : 'Offline'}</span>
            </div>
            {deviceState.state !== 'idle' && deviceState.state !== 'sleep' && (
              <div className="device-state-label">
                {deviceState.state === 'playing' ? '▶️ Playing' :
                 deviceState.state === 'paused' ? '⏸️ Paused' :
                 deviceState.state === 'listening' ? '🎤 Listening' :
                 deviceState.state === 'processing' ? '⚡ Processing' : ''}
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              onClick={() => setMobileOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              {!collapsed && <span className="nav-label">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="sidebar-footer">
          {!collapsed && user && (
            <div className="sidebar-user">
              <div className="user-avatar">👤</div>
              <div className="user-info">
                <div className="user-name">{user.display_name}</div>
                <div className="user-email">{user.email}</div>
              </div>
            </div>
          )}
          <button className="nav-item logout-btn" onClick={logout}>
            <span className="nav-icon">🚪</span>
            {!collapsed && <span className="nav-label">Logout</span>}
          </button>
        </div>
      </aside>

      <style>{`
        .mobile-header {
          display: none;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          height: var(--header-height);
          background: var(--color-bg-sidebar);
          color: white;
          align-items: center;
          padding: 0 16px;
          z-index: 1001;
          gap: 12px;
        }
        .mobile-menu-btn {
          background: none;
          border: none;
          color: white;
          font-size: 1.5rem;
          padding: 4px;
        }
        .mobile-title {
          font-family: var(--font-heading);
          font-weight: 700;
          font-size: 1.125rem;
        }
        .mobile-status { margin-left: auto; }

        .sidebar-overlay {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.5);
          z-index: 999;
        }

        .sidebar {
          position: fixed;
          top: 0;
          left: 0;
          bottom: 0;
          width: var(--sidebar-width);
          background: var(--color-bg-sidebar);
          color: rgba(255,255,255,0.8);
          display: flex;
          flex-direction: column;
          z-index: 1000;
          transition: width var(--transition-base), transform var(--transition-base);
          overflow-y: auto;
        }
        .sidebar.collapsed { width: 72px; }

        .sidebar-logo {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 20px 20px 16px;
        }
        .logo-icon {
          font-size: 1.75rem;
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255,255,255,0.1);
          border-radius: var(--radius-md);
        }
        .logo-text {
          font-family: var(--font-heading);
          font-weight: 800;
          font-size: 1.25rem;
          color: white;
        }

        .sidebar-device-status {
          margin: 0 16px 16px;
          padding: 12px;
          background: rgba(255,255,255,0.06);
          border-radius: var(--radius-md);
          font-size: 0.8125rem;
        }
        .device-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--color-text-muted);
        }
        .status-dot, .device-indicator.online .status-dot {
          background: var(--color-success);
          box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
        }
        .device-indicator.offline .status-dot {
          background: var(--color-text-muted);
          box-shadow: none;
        }
        .device-state-label {
          margin-top: 6px;
          font-size: 0.75rem;
          color: rgba(255,255,255,0.5);
        }

        .sidebar-nav {
          flex: 1;
          padding: 8px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: var(--radius-md);
          color: rgba(255,255,255,0.6);
          font-size: 0.875rem;
          font-weight: 500;
          transition: all var(--transition-fast);
          border: none;
          background: none;
          width: 100%;
          text-align: left;
        }
        .nav-item:hover {
          background: rgba(255,255,255,0.08);
          color: white;
        }
        .nav-item.active {
          background: rgba(79, 70, 229, 0.3);
          color: white;
          font-weight: 600;
        }
        .nav-icon { font-size: 1.125rem; width: 24px; text-align: center; }

        .sidebar-footer {
          padding: 8px;
          border-top: 1px solid rgba(255,255,255,0.08);
          margin-top: auto;
        }
        .sidebar-user {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          margin-bottom: 4px;
        }
        .user-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(255,255,255,0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1rem;
        }
        .user-name {
          font-size: 0.8125rem;
          font-weight: 600;
          color: white;
        }
        .user-email {
          font-size: 0.6875rem;
          color: rgba(255,255,255,0.4);
        }
        .logout-btn { color: rgba(255,255,255,0.4) !important; }
        .logout-btn:hover { color: var(--color-accent) !important; }

        @media (max-width: 768px) {
          .mobile-header { display: flex; }
          .sidebar-overlay { display: block; }
          .sidebar {
            transform: translateX(-100%);
          }
          .sidebar.mobile-open {
            transform: translateX(0);
          }
        }
      `}</style>
    </>
  );
}
