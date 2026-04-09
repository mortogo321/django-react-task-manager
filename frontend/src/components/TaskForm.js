import React, { useState } from 'react';
import Modal from './Modal';
import { tasksApi } from '../api/client';

const PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

export default function TaskForm({ workers = [], onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    worker: '',
    priority: 'medium',
    due_date: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [globalError, setGlobalError] = useState(null);

  const update = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setErrors({ ...errors, [field]: undefined });
  };

  const validate = () => {
    const next = {};
    if (!form.title.trim()) next.title = 'Title is required.';
    if (form.title.length > 200) next.title = 'Title is too long.';
    if (form.description.length > 5000) next.description = 'Description is too long.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (e) => {
    e.preventDefault();
    setGlobalError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        title: form.title.trim(),
        description: form.description.trim(),
        priority: form.priority,
      };
      if (form.worker) payload.worker = Number(form.worker);
      if (form.due_date) payload.due_date = new Date(form.due_date).toISOString();
      const { data } = await tasksApi.create(payload);
      onCreated?.(data);
      onClose?.();
    } catch (err) {
      // Map field errors back into the form, plus a global fallback.
      const data = err.response?.data;
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const fields = {};
        Object.entries(data).forEach(([k, v]) => {
          fields[k] = Array.isArray(v) ? v.join(' ') : String(v);
        });
        setErrors(fields);
      }
      setGlobalError(err.userMessage || 'Failed to create task.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Create task" onClose={onClose}
      footer={
        <>
          <button type="button" className="button button--ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" form="task-form" className="button button--primary" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create task'}
          </button>
        </>
      }
    >
      {globalError && <div className="alert alert--error">{globalError}</div>}
      <form id="task-form" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="task-title">Title</label>
          <input
            id="task-title"
            className="input"
            value={form.title}
            onChange={update('title')}
            maxLength={200}
            required
            autoFocus
          />
          {errors.title && <div className="field__error">{errors.title}</div>}
        </div>
        <div className="field">
          <label htmlFor="task-desc">Description</label>
          <textarea
            id="task-desc"
            className="textarea"
            value={form.description}
            onChange={update('description')}
            maxLength={5000}
          />
          {errors.description && <div className="field__error">{errors.description}</div>}
        </div>
        <div className="field">
          <label htmlFor="task-priority">Priority</label>
          <select
            id="task-priority"
            className="select"
            value={form.priority}
            onChange={update('priority')}
          >
            {PRIORITIES.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="task-worker">Assign worker (optional)</label>
          <select
            id="task-worker"
            className="select"
            value={form.worker}
            onChange={update('worker')}
          >
            <option value="">— unassigned —</option>
            {workers.map((w) => (
              <option key={w.id} value={w.id}>
                {w.first_name} {w.last_name} {w.nickname ? `“${w.nickname}”` : ''} · {w.role_display}
              </option>
            ))}
          </select>
          {errors.worker && <div className="field__error">{errors.worker}</div>}
        </div>
        <div className="field">
          <label htmlFor="task-due">Due date (optional)</label>
          <input
            id="task-due"
            className="input"
            type="datetime-local"
            value={form.due_date}
            onChange={update('due_date')}
          />
          {errors.due_date && <div className="field__error">{errors.due_date}</div>}
        </div>
      </form>
    </Modal>
  );
}
