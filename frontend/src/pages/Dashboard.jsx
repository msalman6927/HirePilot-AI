import { useEffect, useState } from 'react';
import {
  LayoutDashboard, FileText, Briefcase, Mail, Activity, Clock,
  Loader2, RefreshCw, CheckCircle, XCircle, AlertCircle, Search,
} from 'lucide-react';
import useAppStore from '../store/appStore';
import {
  getDashboardCVVersions, getDashboardApplications,
  getAgentLogs, getDashboardJobs,
} from '../services/api';

const TABS = [
  { id: 'cv', label: 'Uploaded CVs', icon: FileText },
  { id: 'jobs', label: 'Job History', icon: Briefcase },
  { id: 'applications', label: 'Applications', icon: Mail },
  { id: 'logs', label: 'Agent Logs', icon: Activity },
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('cv');

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <LayoutDashboard className="w-6 h-6 text-blue-400" />
          Dashboard
        </h1>
        <p className="text-slate-500 mt-1">Track your CV versions, jobs, applications, and agent activity</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#0d1225] border border-[#1e293b] rounded-xl p-1 w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === id
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-[#1a1f35]'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'cv' && <CVVersionsTab />}
      {activeTab === 'jobs' && <JobHistoryTab />}
      {activeTab === 'applications' && <ApplicationsTab />}
      {activeTab === 'logs' && <AgentLogsTab />}
    </div>
  );
}

// ── CV Versions Tab ──────────────────────────────────────────
function CVVersionsTab() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardCVVersions()
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TabLoading />;
  if (data.length === 0) return <TabEmpty text="No CV versions uploaded yet" />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {data.map((cv) => (
        <div key={cv.id} className="bg-[#111827] border border-[#1e293b] rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">{cv.filename}</p>
              <p className="text-xs text-slate-500">
                {cv.created_at ? new Date(cv.created_at).toLocaleDateString() : 'Unknown date'}
              </p>
            </div>
          </div>
          {cv.skills_count != null && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded-full">
                {cv.skills_count} skills
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Job History Tab ──────────────────────────────────────────
function JobHistoryTab() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardJobs()
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TabLoading />;
  if (data.length === 0) return <TabEmpty text="No jobs fetched yet" />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="text-xs text-slate-500 uppercase border-b border-[#1e293b]">
            <th className="pb-3 pr-4">Title</th>
            <th className="pb-3 pr-4">Company</th>
            <th className="pb-3 pr-4">Location</th>
            <th className="pb-3 pr-4">Platform</th>
            <th className="pb-3 pr-4">Match</th>
            <th className="pb-3">Date</th>
          </tr>
        </thead>
        <tbody>
          {data.map((j, i) => (
            <tr key={j.id || i} className="border-b border-[#1e293b]/50 hover:bg-[#1a1f35] transition-colors">
              <td className="py-3 pr-4 text-slate-200 font-medium">{j.title}</td>
              <td className="py-3 pr-4 text-blue-400">{j.company}</td>
              <td className="py-3 pr-4 text-slate-400">{j.location || '—'}</td>
              <td className="py-3 pr-4">
                <span className="px-2 py-0.5 text-xs bg-slate-800 text-slate-400 rounded capitalize">
                  {j.platform || '—'}
                </span>
              </td>
              <td className="py-3 pr-4">
                {j.match_score ? (
                  <span className="text-green-400 font-medium">{Math.round(j.match_score)}%</span>
                ) : '—'}
              </td>
              <td className="py-3 text-slate-500 text-xs">
                {j.fetched_at ? new Date(j.fetched_at).toLocaleDateString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Applications Tab ─────────────────────────────────────────
function ApplicationsTab() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardApplications()
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TabLoading />;
  if (data.length === 0) return <TabEmpty text="No applications sent yet" />;

  const statusColors = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    yellow: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="text-xs text-slate-500 uppercase border-b border-[#1e293b]">
            <th className="pb-3 pr-4">Job Title</th>
            <th className="pb-3 pr-4">Company</th>
            <th className="pb-3 pr-4">HR Email</th>
            <th className="pb-3 pr-4">Status</th>
            <th className="pb-3">Sent At</th>
          </tr>
        </thead>
        <tbody>
          {data.map((app, i) => (
            <tr key={app.id || i} className="border-b border-[#1e293b]/50 hover:bg-[#1a1f35] transition-colors">
              <td className="py-3 pr-4 text-slate-200 font-medium">{app.job_title}</td>
              <td className="py-3 pr-4 text-blue-400">{app.company}</td>
              <td className="py-3 pr-4 text-slate-400">{app.hr_email || '—'}</td>
              <td className="py-3 pr-4">
                <span className={`px-2.5 py-1 text-xs font-medium border rounded-full ${
                  statusColors[app.status_color] || statusColors.blue
                }`}>
                  {app.status}
                </span>
              </td>
              <td className="py-3 text-slate-500 text-xs">
                {app.sent_at ? new Date(app.sent_at).toLocaleString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Agent Logs Tab ───────────────────────────────────────────
function AgentLogsTab() {
  const { sessionId } = useAppStore();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = () => {
    setLoading(true);
    getAgentLogs(sessionId)
      .then((d) => setData(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
    // Poll every 3 seconds
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [sessionId]);

  if (loading && data.length === 0) return <TabLoading />;
  if (data.length === 0) return <TabEmpty text="No agent activity yet" />;

  const statusIcons = {
    completed: <CheckCircle className="w-4 h-4 text-green-400" />,
    running: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
    failed: <XCircle className="w-4 h-4 text-red-400" />,
    success: <CheckCircle className="w-4 h-4 text-green-400" />,
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-slate-500">Session: {sessionId?.slice(0, 8)}...</p>
        <button onClick={fetchLogs} className="flex items-center gap-1 text-xs text-slate-500 hover:text-blue-400 transition-colors">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>
      <div className="space-y-2">
        {data.map((log, i) => (
          <div key={log.id || i} className="flex items-start gap-3 bg-[#111827] border border-[#1e293b] rounded-xl p-4">
            <div className="mt-0.5">
              {statusIcons[log.status] || <Activity className="w-4 h-4 text-slate-500" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-slate-200">{log.agent_name}</span>
                <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                  log.status === 'completed' || log.status === 'success'
                    ? 'bg-green-500/10 text-green-400'
                    : log.status === 'running'
                    ? 'bg-blue-500/10 text-blue-400'
                    : log.status === 'failed'
                    ? 'bg-red-500/10 text-red-400'
                    : 'bg-slate-800 text-slate-500'
                }`}>
                  {log.status}
                </span>
              </div>
              <p className="text-xs text-slate-400">{log.action}</p>
            </div>
            <div className="text-[10px] text-slate-600 whitespace-nowrap">
              {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Shared Components ────────────────────────────────────────
function TabLoading() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
    </div>
  );
}

function TabEmpty({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircle className="w-8 h-8 text-slate-700 mb-3" />
      <p className="text-slate-500">{text}</p>
    </div>
  );
}
