import { useState, useEffect } from 'react';
import { api } from '../api/client';

const CATEGORIES = [
  { id: '', label: 'All', icon: '📖' },
  { id: 'audiobook', label: 'Audiobooks', icon: '📚' },
  { id: 'music', label: 'Music', icon: '🎵' },
  { id: 'story', label: 'Stories', icon: '🌙' },
  { id: 'educational', label: 'Educational', icon: '🎓' },
];

const AGE_GROUPS = [
  { label: 'All Ages', min: 0, max: 12 },
  { label: '0-3', min: 0, max: 3 },
  { label: '3-6', min: 3, max: 6 },
  { label: '6-9', min: 6, max: 9 },
  { label: '9-12', min: 9, max: 12 },
];

export default function Library() {
  const [content, setContent] = useState([]);
  const [category, setCategory] = useState('');
  const [ageGroup, setAgeGroup] = useState(AGE_GROUPS[0]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // Upload states
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadData, setUploadData] = useState({
    title: '', author: '', description: '', category: 'audiobook', age_min: 0, age_max: 12
  });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const fetchContent = () => {
    setLoading(true);
    const params = {};
    if (category) params.category = category;
    if (search) params.search = search;
    params.age_min = ageGroup.min;
    params.age_max = ageGroup.max;

    api.getContent(params)
      .then(setContent)
      .catch(() => setContent([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchContent();
  }, [category, ageGroup, search]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('title', uploadData.title);
      formData.append('file', uploadFile);
      if (uploadData.author) formData.append('author', uploadData.author);
      if (uploadData.description) formData.append('description', uploadData.description);
      formData.append('category', uploadData.category);
      formData.append('age_min', uploadData.age_min);
      formData.append('age_max', uploadData.age_max);

      await api.uploadContent(formData);
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadData({
        title: '', author: '', description: '', category: 'audiobook', age_min: 0, age_max: 12
      });
      fetchContent(); // Refresh content
    } catch (error) {
      console.error('Failed to upload content:', error);
      alert('Failed to upload content');
    } finally {
      setUploading(false);
    }
  };

  const formatDuration = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Content Library</h1>
          <p>Discover audiobooks, music, and stories for your kids</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUploadModal(true)}>
          + Upload Content
        </button>
      </div>

      {/* Filters */}
      <div className="library-filters card" style={{ marginBottom: 24 }}>
        <div className="filter-row">
          {/* Search */}
          <div className="filter-search">
            <input
              className="input"
              type="text"
              placeholder="🔍 Search titles, authors..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              id="library-search"
            />
          </div>

          {/* Age filter */}
          <div className="filter-age">
            {AGE_GROUPS.map(ag => (
              <button
                key={ag.label}
                className={`btn ${ageGroup.label === ag.label ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAgeGroup(ag)}
                style={{ padding: '6px 14px', fontSize: '0.8125rem' }}
              >
                {ag.label}
              </button>
            ))}
          </div>
        </div>

        {/* Category tabs */}
        <div className="filter-categories">
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              className={`category-tab ${category === cat.id ? 'active' : ''}`}
              onClick={() => setCategory(cat.id)}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content Grid */}
      {loading ? (
        <div className="grid grid-3">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="card">
              <div className="skeleton" style={{ height: 140, marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 18, width: '70%', marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 14, width: '50%' }} />
            </div>
          ))}
        </div>
      ) : content.length === 0 ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>📚</div>
          <h3>No content found</h3>
          <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>
            Try adjusting your filters or search terms.
          </p>
        </div>
      ) : (
        <div className="grid grid-3">
          {content.map(item => (
            <div key={item.id} className="card content-card">
              <div className="content-cover">
                <span className="content-cover-icon">
                  {item.category === 'audiobook' ? '📖' :
                   item.category === 'music' ? '🎵' :
                   item.category === 'story' ? '🌙' : '🎓'}
                </span>
              </div>
              <div className="content-info">
                <h3 className="content-title">{item.title}</h3>
                <p className="content-author">{item.author}</p>
                <div className="content-meta">
                  <span className="badge badge-age">Ages {item.age_min}-{item.age_max}</span>
                  <span className="content-duration">
                    ⏱ {formatDuration(item.duration_seconds)}
                  </span>
                </div>
                {item.description && (
                  <p className="content-desc">{item.description}</p>
                )}
                <div style={{ marginTop: '16px' }} onClick={e => e.stopPropagation()}>
                  <audio 
                    controls 
                    src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/content/${item.id}/download`} 
                    style={{ width: '100%', height: '36px', outline: 'none' }} 
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload Content</h2>
              <button className="btn-close" onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <form onSubmit={handleUpload}>
              <div className="form-group">
                <label>File (Audio/MP3)</label>
                <input type="file" className="input" accept="audio/*" required onChange={e => setUploadFile(e.target.files[0])} />
              </div>
              <div className="form-group">
                <label>Title</label>
                <input type="text" className="input" required value={uploadData.title} onChange={e => setUploadData({...uploadData, title: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Author (optional)</label>
                <input type="text" className="input" value={uploadData.author} onChange={e => setUploadData({...uploadData, author: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Description (optional)</label>
                <textarea className="input" style={{ resize: 'vertical', minHeight: '80px' }} value={uploadData.description} onChange={e => setUploadData({...uploadData, description: e.target.value})} />
              </div>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label>Category</label>
                  <select className="input" value={uploadData.category} onChange={e => setUploadData({...uploadData, category: e.target.value})}>
                    {CATEGORIES.filter(c => c.id !== '').map(c => (
                      <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label>Age Min</label>
                  <input type="number" className="input" min="0" max="12" value={uploadData.age_min} onChange={e => setUploadData({...uploadData, age_min: parseInt(e.target.value)})} />
                </div>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label>Age Max</label>
                  <input type="number" className="input" min="0" max="18" value={uploadData.age_max} onChange={e => setUploadData({...uploadData, age_max: parseInt(e.target.value)})} />
                </div>
              </div>
              <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUploadModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={uploading || !uploadFile}>
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        .library-filters { padding: 16px 20px; }
        .filter-row {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
          margin-bottom: 12px;
        }
        .filter-search { flex: 1; min-width: 200px; }
        .filter-age { display: flex; gap: 6px; flex-wrap: wrap; }
        .filter-categories {
          display: flex;
          gap: 4px;
          border-top: 1px solid var(--color-border-light);
          padding-top: 12px;
        }
        .category-tab {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border: none;
          background: none;
          border-radius: var(--radius-full);
          font-size: 0.8125rem;
          font-weight: 500;
          color: var(--color-text-secondary);
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .category-tab:hover { background: var(--color-bg-hover); }
        .category-tab.active {
          background: var(--color-primary-soft);
          color: var(--color-primary);
          font-weight: 600;
        }
        .content-card {
          padding: 0;
          overflow: hidden;
          transition: transform var(--transition-spring), box-shadow var(--transition-base);
        }
        .content-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-lg);
        }
        .content-cover {
          height: 140px;
          background: linear-gradient(135deg, var(--color-primary-soft), rgba(249,112,102,0.08));
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .content-cover-icon { font-size: 3rem; }
        .content-info { padding: 16px; }
        .content-title {
          font-family: var(--font-heading);
          font-size: 0.9375rem;
          font-weight: 700;
          margin-bottom: 4px;
        }
        .content-author {
          font-size: 0.8125rem;
          color: var(--color-text-secondary);
          margin-bottom: 10px;
        }
        .content-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        .content-duration {
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .content-desc {
          font-size: 0.8125rem;
          color: var(--color-text-secondary);
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        
        .modal-overlay {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex; align-items: center; justify-content: center;
          z-index: 1000;
          backdrop-filter: blur(4px);
        }
        .modal-content {
          background: var(--color-bg-primary);
          border-radius: var(--radius-lg);
          padding: 24px;
          width: 100%; max-width: 500px;
          box-shadow: var(--shadow-xl);
          animation: modalIn var(--transition-spring);
        }
        @keyframes modalIn {
          from { opacity: 0; transform: scale(0.95) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .modal-header {
          display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
        }
        .modal-header h2 {
          font-family: var(--font-heading);
          font-size: 1.25rem;
          font-weight: 700;
        }
        .btn-close {
          background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--color-text-muted);
        }
        .btn-close:hover { color: var(--color-text-primary); }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 500; font-size: 0.875rem; color: var(--color-text-secondary); }
        .form-group .input { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border-light); border-radius: var(--radius-md); font-family: inherit; font-size: 0.9375rem; transition: border-color var(--transition-fast); background: var(--color-bg-primary); }
        .form-group .input:focus { outline: none; border-color: var(--color-primary); }

        @media (max-width: 640px) {
          .filter-row { flex-direction: column; }
        }
      `}</style>
    </div>
  );
}
