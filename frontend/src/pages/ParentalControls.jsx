import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function ParentalControls() {
  const [rules, setRules] = useState({
    daily_limit_minutes: 120,
    bedtime_start: '20:00',
    bedtime_end: '07:00',
    volume_cap: 80,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [searches, setSearches] = useState([]);
  const [memoryFacts, setMemoryFacts] = useState([]);

  const fetchSearches = () => {
    api.getSearchHistory().then(setSearches).catch(() => {});
  };

  const fetchMemoryFacts = () => {
    api.getMemoryFacts().then(setMemoryFacts).catch(() => {});
  };

  useEffect(() => {
    api.getParentalRules().then(data => {
      if (data && typeof data === 'object') {
        setRules(prev => ({ ...prev, ...data }));
      }
    }).catch(() => {});
    
    fetchSearches();
    fetchMemoryFacts();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateParentalRules(rules);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error('Failed to save rules:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleClearSearches = async () => {
    if (confirm('Are you sure you want to clear the search history?')) {
      await api.clearSearchHistory();
      fetchSearches();
    }
  };

  const handleDeleteMemoryFact = async (factId) => {
    if (confirm('Delete this memory fact? Mika will no longer remember it.')) {
      await api.deleteMemoryFact(factId);
      fetchMemoryFacts();
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Parental Controls</h1>
        <p>Set boundaries to keep listening healthy and fun</p>
      </div>

      <div className="controls-grid">
        {/* Daily Time Limit */}
        <div className="card control-card">
          <div className="control-header">
            <div className="control-icon">⏰</div>
            <div>
              <h3>Daily Time Limit</h3>
              <p>Maximum listening time per day</p>
            </div>
          </div>
          <div className="control-value-display">
            <span className="control-big-value">{rules.daily_limit_minutes}</span>
            <span className="control-unit">minutes</span>
          </div>
          <input
            type="range"
            className="slider"
            min="15"
            max="480"
            step="15"
            value={rules.daily_limit_minutes}
            onChange={e => setRules({ ...rules, daily_limit_minutes: parseInt(e.target.value) })}
            id="daily-limit-slider"
          />
          <div className="slider-labels">
            <span>15m</span>
            <span>8h</span>
          </div>
        </div>

        {/* Volume Cap */}
        <div className="card control-card">
          <div className="control-header">
            <div className="control-icon">🔊</div>
            <div>
              <h3>Volume Cap</h3>
              <p>Maximum volume level</p>
            </div>
          </div>
          <div className="control-value-display">
            <span className="control-big-value">{rules.volume_cap}</span>
            <span className="control-unit">%</span>
          </div>
          <input
            type="range"
            className="slider"
            min="10"
            max="100"
            step="5"
            value={rules.volume_cap}
            onChange={e => setRules({ ...rules, volume_cap: parseInt(e.target.value) })}
            id="volume-cap-slider"
          />
          <div className="slider-labels">
            <span>10%</span>
            <span>100%</span>
          </div>
        </div>

        {/* Bedtime Start */}
        <div className="card control-card">
          <div className="control-header">
            <div className="control-icon">🌙</div>
            <div>
              <h3>Bedtime Start</h3>
              <p>MikaBox goes quiet at this time</p>
            </div>
          </div>
          <div className="control-time-input">
            <input
              type="time"
              className="input"
              value={rules.bedtime_start}
              onChange={e => setRules({ ...rules, bedtime_start: e.target.value })}
              id="bedtime-start-input"
            />
          </div>
        </div>

        {/* Bedtime End */}
        <div className="card control-card">
          <div className="control-header">
            <div className="control-icon">🌅</div>
            <div>
              <h3>Wake Up Time</h3>
              <p>MikaBox wakes up at this time</p>
            </div>
          </div>
          <div className="control-time-input">
            <input
              type="time"
              className="input"
              value={rules.bedtime_end}
              onChange={e => setRules({ ...rules, bedtime_end: e.target.value })}
              id="bedtime-end-input"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="controls-save">
        <button
          className={`btn ${saved ? 'btn-success-custom' : 'btn-primary'} btn-lg`}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? '⏳ Saving...' : saved ? '✅ Saved!' : '💾 Save & Sync to Device'}
        </button>
      </div>

      {/* Search History */}
      <div className="card" style={{ marginTop: '40px' }}>
        <div className="card-header">
          <span className="card-title">Recent Web Searches</span>
          {searches.length > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={handleClearSearches}>
              Clear History
            </button>
          )}
        </div>
        
        {searches.length > 0 ? (
          <div className="search-history-list">
            {searches.map(search => {
              const date = new Date(search.created_at);
              return (
                <div key={search.id} className="search-history-item">
                  <div className="search-history-query">"{search.query}"</div>
                  <div className="search-history-time">
                    {date.toLocaleDateString()} at {date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '32px 0' }}>
            No recent searches. When MikaBox searches the web for answers, they will appear here.
          </div>
        )}
      </div>

      {/* Memory Facts */}
      <div className="card" style={{ marginTop: '40px' }}>
        <div className="card-header">
          <span className="card-title">Mika's Memory</span>
        </div>
        
        {memoryFacts.length > 0 ? (
          <div className="search-history-list">
            {memoryFacts.map(fact => {
              const date = new Date(fact.created_at);
              return (
                <div key={fact.id} className="search-history-item" style={{ alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div className="search-history-query">{fact.fact}</div>
                    <div className="search-history-time">
                      Learned on {date.toLocaleDateString()}
                    </div>
                  </div>
                  <button 
                    className="btn btn-secondary btn-sm" 
                    onClick={() => handleDeleteMemoryFact(fact.id)}
                    style={{ color: 'var(--color-danger)', borderColor: 'transparent', padding: '4px 8px' }}
                  >
                    Delete
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '32px 0' }}>
            Mika hasn't learned any personal facts yet. When your child shares their likes, dislikes, or personal details, Mika will remember them here.
          </div>
        )}
      </div>

      <style>{`
        .controls-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 20px;
        }
        @media (max-width: 768px) {
          .controls-grid { grid-template-columns: 1fr; }
        }
        .control-card {
          padding: 24px;
        }
        .control-header {
          display: flex;
          align-items: flex-start;
          gap: 14px;
          margin-bottom: 20px;
        }
        .control-icon {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-md);
          background: var(--color-primary-soft);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.25rem;
          flex-shrink: 0;
        }
        .control-header h3 {
          font-family: var(--font-heading);
          font-size: 1rem;
          font-weight: 700;
          margin-bottom: 2px;
        }
        .control-header p {
          font-size: 0.8125rem;
          color: var(--color-text-secondary);
        }
        .control-value-display {
          text-align: center;
          margin-bottom: 16px;
        }
        .control-big-value {
          font-family: var(--font-heading);
          font-size: 2.5rem;
          font-weight: 800;
          background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .control-unit {
          font-size: 0.875rem;
          color: var(--color-text-muted);
          margin-left: 4px;
        }
        .slider-labels {
          display: flex;
          justify-content: space-between;
          margin-top: 8px;
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .control-time-input {
          margin-top: 8px;
        }
        .control-time-input .input {
          width: 100%;
          font-size: 1.5rem;
          font-family: var(--font-heading);
          font-weight: 700;
          text-align: center;
          padding: 12px;
        }
        .controls-save {
          margin-top: 24px;
          text-align: center;
        }
        .btn-success-custom {
          background: linear-gradient(135deg, var(--color-success), #059669) !important;
          color: white;
          box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }
        .search-history-list {
          display: flex;
          flex-direction: column;
        }
        .search-history-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 0;
          border-bottom: 1px solid var(--color-border-light);
        }
        .search-history-item:last-child {
          border-bottom: none;
        }
        .search-history-query {
          font-weight: 600;
          color: var(--color-text);
          font-size: 0.9375rem;
        }
        .search-history-time {
          font-size: 0.8125rem;
          color: var(--color-text-muted);
        }
      `}</style>
    </div>
  );
}
