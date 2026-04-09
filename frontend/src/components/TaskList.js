import React, { useCallback, useEffect, useState } from 'react';
import { tasksApi, workersApi, unwrapList } from '../api/client';
import TaskForm from './TaskForm';

const STATUS_LABELS = {
  created:     { label: 'Created',     color: '#6b7280' },
  assigned:    { label: 'Assigned',    color: '#2563eb' },
  in_progress: { label: 'In Progress', color: '#f59e0b' },
  completed:   { label: 'Completed',   color: '#16a34a' },
  verified:    { label: 'Verified',    color: '#9333ea' },
};

const PRIORITY_LABELS = {
  low:    { label: 'Low',    color: '#84cc16' },
  medium: { label: 'Medium', color: '#facc15' },
  high:   { label: 'High',   color: '#f97316' },
  urgent: { label: 'Urgent', color: '#dc2626' },
};

// Mirrors backend TASK_TRANSITIONS so the UI never offers an illegal move.
const TRANSITIONS = {
  created:     ['assigned', 'in_progress'],
  assigned:    ['in_progress'],
  in_progress: ['completed'],
  completed:   ['verified'],
  verified:    [],
};

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [stats, setStats] = useState(null);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const params = statusFilter ? { status: statusFilter } : {};
      const { data } = await tasksApi.list(params);
      setTasks(unwrapList(data).results);
      setError(null);
    } catch (err) {
      setError(err.userMessage || 'Failed to load tasks.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await tasksApi.stats();
      setStats(data);
    } catch (err) {
      // Stats are decorative — log but don't crash the page.
      console.error(err);
    }
  }, []);

  const fetchWorkers = useCallback(async () => {
    try {
      const { data } = await workersApi.list({ is_active: true });
      setWorkers(unwrapList(data).results);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchStats();
  }, [fetchTasks, fetchStats]);

  useEffect(() => {
    fetchWorkers();
  }, [fetchWorkers]);

  const transition = async (taskId, status) => {
    setBusyId(taskId);
    try {
      const { data } = await tasksApi.transition(taskId, status);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? data : t)));
      fetchStats();
    } catch (err) {
      setError(err.userMessage || 'Could not update task status.');
    } finally {
      setBusyId(null);
    }
  };

  const onCreated = (task) => {
    setTasks((prev) => [task, ...prev]);
    fetchStats();
  };

  return (
    <section className="tasks">
      <div className="section-header">
        <h2>Tasks{tasks.length ? ` (${tasks.length})` : ''}</h2>
        <div className="task-toolbar">
          <select
            className="select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([key, val]) => (
              <option key={key} value={key}>{val.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="button button--primary"
            onClick={() => setCreating(true)}
          >
            + New task
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert--error" role="alert">
          <span>{error}</span>
          <button type="button" className="button button--ghost" onClick={fetchTasks}>
            Retry
          </button>
        </div>
      )}

      {stats && (
        <div className="stats-bar" aria-label="Task stats">
          {Object.entries(stats.by_status || {}).map(([status, count]) => (
            <div key={status} className="stats-bar__item">
              <span
                className="stats-bar__dot"
                style={{ backgroundColor: STATUS_LABELS[status]?.color || '#ccc' }}
              />
              <span>{STATUS_LABELS[status]?.label || status}: <strong>{count}</strong></span>
            </div>
          ))}
          {typeof stats.overdue === 'number' && (
            <div className="stats-bar__item">
              <span className="stats-bar__dot" style={{ backgroundColor: '#dc2626' }} />
              <span>Overdue: <strong>{stats.overdue}</strong></span>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading-block">
          <span className="spinner" />
          Loading tasks…
        </div>
      ) : tasks.length === 0 ? (
        <div className="card empty-state">
          <strong>No tasks yet</strong>
          Create your first task to assign work to your staff.
        </div>
      ) : (
        <div className="task-list">
          {tasks.map((task) => {
            const statusInfo = STATUS_LABELS[task.status] || {};
            const priorityInfo = PRIORITY_LABELS[task.priority] || {};
            const next = TRANSITIONS[task.status] || [];
            return (
              <article key={task.id} className="task-card">
                <div className="task-card__header">
                  <div>
                    <div className="task-card__title">{task.title}</div>
                    {task.title_th && (
                      <div className="task-card__title-th">🇹🇭 {task.title_th}</div>
                    )}
                  </div>
                  <span
                    className="badge"
                    style={{ background: priorityInfo.color, color: '#fff' }}
                  >
                    {priorityInfo.label}
                  </span>
                </div>

                {task.description && (
                  <div className="task-card__desc">{task.description}</div>
                )}
                {task.description_th && (
                  <div className="task-card__desc">🇹🇭 {task.description_th}</div>
                )}

                <div className="task-card__meta">
                  <span
                    className="badge badge--bordered"
                    style={{ color: statusInfo.color, borderColor: statusInfo.color }}
                  >
                    {statusInfo.label}
                  </span>
                  {task.worker_name && <span>👤 {task.worker_name}</span>}
                  {task.due_date && (
                    <span>📅 {new Date(task.due_date).toLocaleString()}</span>
                  )}
                </div>

                {next.length > 0 && (
                  <div className="task-card__actions">
                    {next.map((status) => (
                      <button
                        key={status}
                        type="button"
                        className={`button ${
                          status === 'completed' ? 'button--success' : 'button--ghost'
                        }`}
                        disabled={busyId === task.id}
                        onClick={() => transition(task.id, status)}
                      >
                        {busyId === task.id ? '…' : `→ ${STATUS_LABELS[status]?.label || status}`}
                      </button>
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {creating && (
        <TaskForm
          workers={workers}
          onClose={() => setCreating(false)}
          onCreated={onCreated}
        />
      )}
    </section>
  );
}
