import { useState, useEffect } from 'react';
import { api } from '../api/client';

const AVATARS = ['🐻', '🦁', '🐰', '🦊', '🐸', '🦄', '🐱', '🐶', '🐼', '🦋', '🌟', '🚀'];

export default function Profiles() {
  const [profiles, setProfiles] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ name: '', age: 5, avatar: '🐻' });

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = () => {
    api.getProfiles().then(setProfiles).catch(() => {});
  };

  const handleSave = async () => {
    if (editId) {
      await api.updateProfile(editId, form);
    } else {
      await api.createProfile(form);
    }
    setShowForm(false);
    setEditId(null);
    setForm({ name: '', age: 5, avatar: '🐻' });
    loadProfiles();
  };

  const handleEdit = (profile) => {
    setForm({ name: profile.name, age: profile.age, avatar: profile.avatar });
    setEditId(profile.id);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (confirm('Delete this profile?')) {
      await api.deleteProfile(id);
      loadProfiles();
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1>Child Profiles</h1>
          <p>Manage profiles for your children</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setShowForm(true); setEditId(null); setForm({ name: '', age: 5, avatar: '🐻' }); }}>
          ➕ Add Profile
        </button>
      </div>

      {/* Profile Form */}
      {showForm && (
        <div className="card profile-form animate-fade-in" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>{editId ? 'Edit Profile' : 'New Profile'}</h3>
          <div className="form-grid">
            <div className="input-group">
              <label htmlFor="profile-name">Child's Name</label>
              <input id="profile-name" className="input" type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Name" required />
            </div>
            <div className="input-group">
              <label htmlFor="profile-age">Age</label>
              <input id="profile-age" className="input" type="number" min="0" max="18" value={form.age} onChange={e => setForm({ ...form, age: parseInt(e.target.value) || 0 })} />
            </div>
          </div>
          <div className="input-group mt-md">
            <label>Avatar</label>
            <div className="avatar-grid">
              {AVATARS.map(a => (
                <button key={a} type="button" className={`avatar-option ${form.avatar === a ? 'selected' : ''}`} onClick={() => setForm({ ...form, avatar: a })}>
                  {a}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-sm mt-md">
            <button className="btn btn-primary" onClick={handleSave}>
              {editId ? 'Update' : 'Create'} Profile
            </button>
            <button className="btn btn-secondary" onClick={() => { setShowForm(false); setEditId(null); }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Profile Cards */}
      {profiles.length === 0 ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>👶</div>
          <h3>No profiles yet</h3>
          <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>
            Create a profile for your child to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-3">
          {profiles.map(p => (
            <div key={p.id} className="card profile-card">
              <div className="profile-avatar-lg">{p.avatar}</div>
              <h3>{p.name}</h3>
              <span className="badge badge-age">Age {p.age}</span>
              <div className="profile-actions mt-md">
                <button className="btn btn-secondary" onClick={() => handleEdit(p)}>✏️ Edit</button>
                <button className="btn btn-secondary" onClick={() => handleDelete(p.id)} style={{ color: 'var(--color-error)' }}>🗑️</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .form-grid { display: grid; grid-template-columns: 1fr 100px; gap: 16px; }
        .avatar-grid { display: flex; gap: 8px; flex-wrap: wrap; }
        .avatar-option {
          width: 44px; height: 44px;
          border-radius: var(--radius-md);
          border: 2px solid var(--color-border);
          background: var(--color-bg);
          font-size: 1.25rem;
          display: flex; align-items: center; justify-content: center;
          transition: all var(--transition-fast);
        }
        .avatar-option:hover { border-color: var(--color-primary-light); }
        .avatar-option.selected {
          border-color: var(--color-primary);
          background: var(--color-primary-soft);
          box-shadow: 0 0 0 2px var(--color-primary-soft);
        }
        .profile-card {
          text-align: center;
          padding: 32px 24px;
          transition: transform var(--transition-spring);
        }
        .profile-card:hover { transform: translateY(-4px); }
        .profile-avatar-lg {
          width: 80px; height: 80px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--color-primary-soft), rgba(249,112,102,0.08));
          display: flex; align-items: center; justify-content: center;
          font-size: 2.5rem;
          margin: 0 auto 16px;
        }
        .profile-card h3 { font-family: var(--font-heading); font-size: 1.125rem; margin-bottom: 8px; }
        .profile-actions { display: flex; justify-content: center; gap: 8px; }
      `}</style>
    </div>
  );
}
