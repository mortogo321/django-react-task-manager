import React, { useEffect, useState } from 'react';
import Dashboard from './components/Dashboard';
import NotificationsBell from './components/NotificationsBell';
import TaskList from './components/TaskList';
import WorkerList from './components/WorkerList';
import { employersApi, getEmployerId, healthApi, setEmployerId, unwrapList } from './api/client';

const TABS = [
  { key: 'dashboard', label: '📊 Dashboard' },
  { key: 'tasks',     label: '📋 Tasks' },
  { key: 'workers',   label: '👷 Workers' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('tasks');
  const [health, setHealth] = useState(null);
  const [employers, setEmployers] = useState([]);
  const [currentEmployerId, setCurrentEmployerId] = useState(getEmployerId());

  useEffect(() => {
    healthApi.check()
      .then((res) => setHealth(res.data))
      .catch(() => setHealth({ status: 'unreachable' }));
  }, []);

  useEffect(() => {
    employersApi.list()
      .then((res) => {
        const list = unwrapList(res.data).results;
        setEmployers(list);
        // If the saved id no longer exists, fall back to the first one.
        if (list.length && !list.find((e) => String(e.id) === String(currentEmployerId))) {
          const first = String(list[0].id);
          setEmployerId(first);
          setCurrentEmployerId(first);
        }
      })
      .catch(() => setEmployers([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const switchEmployer = (id) => {
    setEmployerId(id);
    setCurrentEmployerId(id);
    // Force a remount of the active tab so it refetches with the new auth.
    setActiveTab((t) => t);
    window.location.reload();
  };

  const healthOk = health?.status === 'healthy';
  const healthColor = healthOk ? '#22c55e' : health?.status ? '#facc15' : '#f87171';

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">
          <span style={{ fontSize: 26 }}>🏠</span>
          <h1>Task Manager</h1>
          <span className="header__tagline">AI Household Management</span>
        </div>
        <div className="header__right">
          {employers.length > 0 && (
            <select
              className="header__select"
              value={currentEmployerId}
              onChange={(e) => switchEmployer(e.target.value)}
              aria-label="Switch employer"
            >
              {employers.map((e) => (
                <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
              ))}
            </select>
          )}
          <NotificationsBell />
          <span className="health-badge" title={JSON.stringify(health)}>
            <span className="health-dot" style={{ backgroundColor: healthColor }} />
            API: {health?.status || 'checking…'}
          </span>
        </div>
      </header>

      <nav className="nav" aria-label="Primary">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`nav__btn ${activeTab === t.key ? 'nav__btn--active' : ''}`}
            onClick={() => setActiveTab(t.key)}
            aria-current={activeTab === t.key ? 'page' : undefined}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="main">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'tasks' && <TaskList />}
        {activeTab === 'workers' && <WorkerList />}
      </main>

      <footer className="footer">
        Task Manager v0.2.0 · Test build
      </footer>
    </div>
  );
}
