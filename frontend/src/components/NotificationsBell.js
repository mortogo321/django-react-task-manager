import { useCallback, useEffect, useRef, useState } from 'react';
import { notificationsApi, unwrapList } from '../api/client';

const POLL_MS = 30_000;

/**
 * Bell in the header — shows unread count, opens a small dropdown with
 * the latest 10 notifications and lets the user mark them read.
 *
 * Polling pauses when the tab is hidden so we don't burn battery /
 * server quota for an out-of-focus window. Outside-click closes the
 * panel; Esc closes the panel and returns focus to the trigger.
 */
export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const wrapperRef = useRef(null);
  const triggerRef = useRef(null);

  const refreshUnread = useCallback(async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    try {
      const { data } = await notificationsApi.unread();
      setUnread(data.unread || 0);
    } catch {
      // Polling errors are intentionally swallowed.
    }
  }, []);

  useEffect(() => {
    refreshUnread();
    const id = setInterval(refreshUnread, POLL_MS);
    const onVisibility = () => {
      if (!document.hidden) refreshUnread();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [refreshUnread]);

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const togglePanel = async () => {
    const willOpen = !open;
    setOpen(willOpen);
    if (!willOpen) return;
    setLoading(true);
    try {
      const { data } = await notificationsApi.list();
      setItems(unwrapList(data).results.slice(0, 10));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const markAll = async () => {
    try {
      await notificationsApi.markAllRead();
      setUnread(0);
      setItems((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch {
      // ignore
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <button
        ref={triggerRef}
        type="button"
        className="header__select"
        onClick={togglePanel}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Notifications${unread ? ` (${unread} unread)` : ''}`}
      >
        🔔 {unread > 0 && <strong style={{ marginLeft: 4 }}>{unread}</strong>}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            width: 320,
            maxHeight: 420,
            overflowY: 'auto',
            background: '#fff',
            color: '#111827',
            border: '1px solid #e5e7eb',
            borderRadius: 10,
            boxShadow: '0 12px 32px rgba(15,23,42,0.16)',
            zIndex: 50,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 14px',
              borderBottom: '1px solid #e5e7eb',
            }}
          >
            <strong>Notifications</strong>
            {unread > 0 && (
              <button
                type="button"
                className="button button--ghost"
                onClick={markAll}
                style={{ padding: '4px 10px', minHeight: 32 }}
              >
                Mark all read
              </button>
            )}
          </div>
          {loading ? (
            <div className="loading-block" style={{ padding: 18 }}>
              <span className="spinner" />
            </div>
          ) : items.length === 0 ? (
            <div className="empty-state" style={{ padding: '20px 14px' }}>
              <strong>No notifications yet</strong>
              They will appear when you create or update tasks.
            </div>
          ) : (
            items.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: '12px 14px',
                  borderBottom: '1px solid #f3f4f6',
                  background: n.read_at ? '#fff' : '#eff6ff',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title}</div>
                {n.body && (
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{n.body}</div>
                )}
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
