import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// ── CV ────────────────────────────────────────────────────────
export async function uploadCV(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/cv/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return data;
}

export async function getCVVersions() {
  const { data } = await api.get('/cv/versions');
  return data;
}

// ── Chat ──────────────────────────────────────────────────────
export async function sendMessage(message, threadId, context = {}) {
  const { data } = await api.post('/chat/', {
    message,
    thread_id: threadId,
    context,
  });
  return data;
}

// ── Jobs ──────────────────────────────────────────────────────
export async function getJobs(sessionId) {
  const params = sessionId ? { session_id: sessionId } : {};
  const { data } = await api.get('/jobs/', { params });
  return data;
}

export async function getJobById(jobId) {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data;
}

// ── Apply (HITL) ─────────────────────────────────────────────
export async function getApplicationPreview(jobId, sessionId) {
  const { data } = await api.get(`/apply/preview/${jobId}`, {
    params: { session_id: sessionId },
    timeout: 120000,
  });
  return data;
}

export async function approveApplication(sessionId, editedEmailDraft, approved = true) {
  const { data } = await api.post('/apply/approve', {
    session_id: sessionId,
    edited_email_draft: editedEmailDraft,
    approved,
  });
  return data;
}

// ── Dashboard ─────────────────────────────────────────────────
export async function getDashboardCVVersions() {
  const { data } = await api.get('/dashboard/cv-versions');
  return data;
}

export async function getDashboardApplications() {
  const { data } = await api.get('/dashboard/applications');
  return data;
}

export async function getAgentLogs(sessionId) {
  const params = sessionId ? { session_id: sessionId } : {};
  const { data } = await api.get('/dashboard/logs', { params });
  return data;
}

export async function getDashboardJobs() {
  const { data } = await api.get('/dashboard/jobs');
  return data;
}

export default api;
