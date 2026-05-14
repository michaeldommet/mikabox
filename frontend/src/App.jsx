import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { DeviceProvider, useDevice } from './contexts/DeviceContext';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import RemoteControl from './pages/RemoteControl';
import ParentalControls from './pages/ParentalControls';
import Profiles from './pages/Profiles';
import Settings from './pages/Settings';

function SafetyAlertModal() {
  const { deviceState, dismissSafetyAlert } = useDevice();
  const alertReason = deviceState?.safety_alert;

  if (!alertReason) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px'
    }}>
      <div style={{
        background: 'var(--color-bg)',
        padding: '32px',
        borderRadius: 'var(--radius-lg)',
        maxWidth: '500px',
        width: '100%',
        boxShadow: '0 25px 50px -12px rgba(220, 38, 38, 0.4)',
        border: '2px solid var(--color-danger)',
        animation: 'scale-up 0.3s ease-out'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px', color: 'var(--color-danger)' }}>
          <div style={{ fontSize: '3rem', animation: 'pulse-danger 1s infinite' }}>🚨</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>SAFETY ALERT TRIGGERED</h2>
        </div>
        <p style={{ fontSize: '1.125rem', lineHeight: 1.6, marginBottom: '24px', fontWeight: 500 }}>
          MikaBox has detected a potentially dangerous request from your child:
        </p>
        <div style={{
          background: 'rgba(220, 38, 38, 0.1)',
          padding: '16px',
          borderRadius: 'var(--radius-md)',
          borderLeft: '4px solid var(--color-danger)',
          marginBottom: '32px',
          fontSize: '1.25rem',
          fontWeight: 600
        }}>
          "{alertReason}"
        </div>
        <button 
          className="btn btn-primary btn-lg" 
          style={{ width: '100%', background: 'var(--color-danger)' }}
          onClick={dismissSafetyAlert}
        >
          Dismiss Alert
        </button>
      </div>
      <style>{`
        @keyframes pulse-danger {
          0% { transform: scale(1); }
          50% { transform: scale(1.1); filter: brightness(1.2); }
          100% { transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

function ProtectedLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: 16, animation: 'pulse-soft 1.5s ease-in-out infinite' }}>🎵</div>
          <div style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>Loading MikaBox...</div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <DeviceProvider>
      <div className="app-layout">
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/library" element={<Library />} />
            <Route path="/remote" element={<RemoteControl />} />
            <Route path="/controls" element={<ParentalControls />} />
            <Route path="/profiles" element={<Profiles />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <SafetyAlertModal />
      </div>
    </DeviceProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ProtectedLayout />
      </AuthProvider>
    </BrowserRouter>
  );
}
