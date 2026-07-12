import { useCallback, useEffect, useState } from 'react';
import { unwrapList, workersApi } from '../api/client';

const ROLE_BG = {
  maid: '#e3f2fd',
  nanny: '#fce4ec',
  driver: '#e8f5e9',
  cook: '#fff3e0',
  gardener: '#f1f8e9',
  guard: '#ede7f6',
  other: '#f5f5f5',
};

export default function WorkerList() {
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [roleFilter, setRoleFilter] = useState('');

  const fetchWorkers = useCallback(async () => {
    try {
      setLoading(true);
      const params = roleFilter ? { role: roleFilter } : {};
      const { data } = await workersApi.list(params);
      setWorkers(unwrapList(data).results);
      setError(null);
    } catch (err) {
      setError(err.userMessage || 'Failed to load workers.');
    } finally {
      setLoading(false);
    }
  }, [roleFilter]);

  useEffect(() => {
    fetchWorkers();
  }, [fetchWorkers]);

  return (
    <section>
      <div className="section-header">
        <h2>Workers{workers.length ? ` (${workers.length})` : ''}</h2>
        <select
          className="select"
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          aria-label="Filter by role"
          style={{ maxWidth: 220 }}
        >
          <option value="">All roles</option>
          <option value="maid">Maid</option>
          <option value="nanny">Nanny</option>
          <option value="driver">Driver</option>
          <option value="cook">Cook</option>
          <option value="gardener">Gardener</option>
          <option value="guard">Guard</option>
        </select>
      </div>

      {error && (
        <div className="alert alert--error" role="alert">
          <span>{error}</span>
          <button type="button" className="button button--ghost" onClick={fetchWorkers}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="loading-block">
          <span className="spinner" /> Loading workers…
        </div>
      ) : workers.length === 0 ? (
        <div className="card empty-state">
          <strong>No workers yet</strong>
          Add household staff to start assigning tasks.
        </div>
      ) : (
        <div className="workers-grid">
          {workers.map((w) => (
            <div
              key={w.id}
              className="worker-card"
              style={{ background: ROLE_BG[w.role] || '#f5f5f5' }}
            >
              <div className="worker-card__row">
                <strong>
                  {w.first_name} {w.last_name}
                </strong>
                {w.nickname && <em style={{ color: '#666' }}>“{w.nickname}”</em>}
              </div>
              <div className="worker-card__row">
                <span className="worker-card__role-pill">{w.role_display}</span>
                <span className="worker-card__salary">฿{Number(w.salary).toLocaleString()}/mo</span>
              </div>
              <div
                className="worker-card__row"
                style={{
                  fontSize: 12,
                  color: '#555',
                  borderTop: '1px solid rgba(0,0,0,0.06)',
                  paddingTop: 6,
                }}
              >
                <span>Phone: {w.phone}</span>
                <span style={{ color: w.is_active ? '#16a34a' : '#dc2626' }}>
                  {w.is_active ? '● Active' : '○ Inactive'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
