import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

// Persist sessionId across reloads
const getOrCreateSessionId = () => {
  let id = localStorage.getItem('hirepilot_session_id');
  if (!id) {
    id = uuidv4();
    localStorage.setItem('hirepilot_session_id', id);
  }
  return id;
};

const useAppStore = create((set, get) => ({
  // ── Session ─────────────────────────────────────────
  sessionId: getOrCreateSessionId(),
  resetSession: () => {
    const id = uuidv4();
    localStorage.setItem('hirepilot_session_id', id);
    set({ sessionId: id, chatMessages: [], jobs: [], agentLogs: [], selectedJob: null, applicationPreview: null });
  },

  // ── CV ──────────────────────────────────────────────
  parsedCV: null,
  cvId: null,
  setParsedCV: (cv, id) => set({ parsedCV: cv, cvId: id }),

  // ── Chat ────────────────────────────────────────────
  chatMessages: [],
  addChatMessage: (msg) => set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  setChatMessages: (msgs) => set({ chatMessages: msgs }),

  // ── Jobs ────────────────────────────────────────────
  jobs: [],
  setJobs: (jobs) => set({ jobs }),
  selectedJob: null,
  setSelectedJob: (job) => set({ selectedJob: job }),

  // ── Application (HITL) ─────────────────────────────
  applicationPreview: null,
  setApplicationPreview: (preview) => set({ applicationPreview: preview }),

  // ── Agent Logs ──────────────────────────────────────
  agentLogs: [],
  setAgentLogs: (logs) => set({ agentLogs: logs }),

  // ── Loading States ──────────────────────────────────
  isAgentRunning: false,
  setAgentRunning: (v) => set({ isAgentRunning: v }),
  isUploading: false,
  setUploading: (v) => set({ isUploading: v }),
}));

export default useAppStore;
