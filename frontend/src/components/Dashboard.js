import { useCallback, useEffect, useState } from 'react';
import { employersApi, getEmployerId, tasksApi } from '../api/client';

/**
 * Day-5 free feature: lightweight analytics dashboard.
 * Combines billing/headcount from /employers/{id}/dashboard/ with the
 * task stats endpoint, then renders a few inline-SVG bar charts.
 */
export default function Dashboard() {
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const empId = getEmployerId();
      const [dash, taskStats] = await Promise.all([
        employersApi.dashboard(empId),
        tasksApi.stats(),
      ]);
      setData(dash.data);
      setStats(taskStats.data);
    } catch (err) {
      setError(err.userMessage || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="loading-block">
        <span className="spinner" /> Loading dashboard…
      </div>
    );
  }
  if (error) {
    return (
      <div className="alert alert--error" role="alert">
        <span>{error}</span>
        <button type="button" className="button button--ghost" onClick={load}>
          Retry
        </button>
      </div>
    );
  }
  if (!data || !stats) return null;

  const totalTasks = stats.total || 0;
  const completed = (stats.by_status?.completed || 0) + (stats.by_status?.verified || 0);
  const completionRate = totalTasks ? Math.round((completed / totalTasks) * 100) : 0;

  return (
    <section>
      <div className="section-header">
        <h2>Dashboard</h2>
        <button type="button" className="button button--ghost" onClick={load}>
          Refresh
        </button>
      </div>

      <div style={kpiGrid}>
        <KpiCard
          label="Plan"
          value={data.employer.plan}
          sub={`฿${data.billing.plan_price_thb}/mo`}
        />
        <KpiCard
          label="Workers"
          value={`${data.billing.worker_count} / ${data.billing.worker_limit}`}
          sub="active / plan limit"
        />
        <KpiCard
          label="Monthly salary"
          value={`฿${Number(data.billing.total_monthly_salary).toLocaleString()}`}
          sub="sum of active staff"
        />
        <KpiCard label="Total tasks" value={totalTasks} sub={`${completionRate}% completed`} />
        <KpiCard
          label="Overdue"
          value={stats.overdue || 0}
          sub="not done past due date"
          tone={stats.overdue ? 'danger' : 'normal'}
        />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Tasks by status</h3>
        <BarChart data={stats.by_status || {}} colors={STATUS_COLORS} />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Tasks by priority</h3>
        <BarChart data={stats.by_priority || {}} colors={PRIORITY_COLORS} />
      </div>
    </section>
  );
}

const kpiGrid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 12,
};

function KpiCard({ label, value, sub, tone = 'normal' }) {
  return (
    <div className="card">
      <div
        style={{ fontSize: 12, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.4 }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 700,
          marginTop: 6,
          color: tone === 'danger' ? '#dc2626' : '#111827',
        }}
      >
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

const STATUS_COLORS = {
  created: '#6b7280',
  assigned: '#2563eb',
  in_progress: '#f59e0b',
  completed: '#16a34a',
  verified: '#9333ea',
};
const PRIORITY_COLORS = {
  low: '#84cc16',
  medium: '#facc15',
  high: '#f97316',
  urgent: '#dc2626',
};

function BarChart({ data, colors }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Object.entries(data).map(([key, count]) => (
        <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 110, fontSize: 13, color: '#374151', textTransform: 'capitalize' }}>
            {key.replace('_', ' ')}
          </div>
          <div
            style={{
              flex: 1,
              background: '#f3f4f6',
              borderRadius: 999,
              overflow: 'hidden',
              height: 14,
            }}
          >
            <div
              style={{
                width: `${(count / max) * 100}%`,
                height: '100%',
                background: colors[key] || '#9ca3af',
                transition: 'width 240ms ease',
              }}
            />
          </div>
          <div style={{ minWidth: 32, textAlign: 'right', fontWeight: 600 }}>{count}</div>
        </div>
      ))}
    </div>
  );
}
