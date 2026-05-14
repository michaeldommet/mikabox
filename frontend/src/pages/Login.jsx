import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card card-glass animate-fade-in">
        <div className="login-header">
          <div className="login-logo">🎵</div>
          <h1>MikaBox</h1>
          <p>Smart speaker companion for parents</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {isRegister && (
            <div className="input-group">
              <label htmlFor="login-name">Your Name</label>
              <input
                id="login-name"
                className="input"
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Parent name"
                required
              />
            </div>
          )}

          <div className="input-group">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className="input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="parent@email.com"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              minLength={8}
              required
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-lg w-full" disabled={loading}>
            {loading ? '...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>

          <p className="login-toggle">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button type="button" onClick={() => { setIsRegister(!isRegister); setError(''); }}>
              {isRegister ? 'Sign in' : 'Create one'}
            </button>
          </p>
        </form>
      </div>

      <style>{`
        .login-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4338CA 100%);
          padding: 20px;
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          padding: 40px;
          background: rgba(255,255,255,0.95) !important;
        }
        .login-header {
          text-align: center;
          margin-bottom: 32px;
        }
        .login-logo {
          width: 64px;
          height: 64px;
          margin: 0 auto 16px;
          background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
          border-radius: var(--radius-lg);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 2rem;
          box-shadow: 0 8px 24px rgba(79, 70, 229, 0.3);
        }
        .login-header h1 {
          font-family: var(--font-heading);
          font-size: 1.75rem;
          font-weight: 800;
          background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .login-header p {
          color: var(--color-text-secondary);
          font-size: 0.875rem;
          margin-top: 4px;
        }
        .login-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .login-error {
          padding: 10px 14px;
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.2);
          border-radius: var(--radius-md);
          color: var(--color-error);
          font-size: 0.8125rem;
        }
        .login-toggle {
          text-align: center;
          font-size: 0.8125rem;
          color: var(--color-text-secondary);
        }
        .login-toggle button {
          background: none;
          border: none;
          color: var(--color-primary);
          font-weight: 600;
          font-size: inherit;
        }
        .login-toggle button:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}
