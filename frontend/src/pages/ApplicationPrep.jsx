import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileCheck, Mail, Loader2, CheckCircle, XCircle, AlertCircle,
  Edit3, ArrowLeft, ShieldCheck,
} from 'lucide-react';
import useAppStore from '../store/appStore';
import { getApplicationPreview, approveApplication } from '../services/api';

export default function ApplicationPrep() {
  const navigate = useNavigate();
  const { selectedJob, sessionId, applicationPreview, setApplicationPreview } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [approved, setApproved] = useState(false);
  const [emailDraft, setEmailDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [editMode, setEditMode] = useState(false);

  // Fetch HITL preview
  useEffect(() => {
    if (!selectedJob) return;
    const fetchPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getApplicationPreview(selectedJob.id, sessionId);
        setApplicationPreview(data);
        setEmailDraft(data.email_draft || '');
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to generate application preview');
      } finally {
        setLoading(false);
      }
    };
    fetchPreview();
  }, [selectedJob]);

  const handleApprove = async () => {
    setSending(true);
    setError(null);
    try {
      const data = await approveApplication(sessionId, emailDraft, true);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send application');
    } finally {
      setSending(false);
    }
  };

  const handleReject = async () => {
    try {
      await approveApplication(sessionId, emailDraft, false);
      navigate('/jobs');
    } catch {
      navigate('/jobs');
    }
  };

  // No job selected
  if (!selectedJob) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center p-8">
        <FileCheck className="w-12 h-12 text-slate-700 mb-4" />
        <p className="text-slate-500 text-lg">No job selected</p>
        <p className="text-slate-600 text-sm mt-1">Go to Jobs and select one to apply</p>
        <button
          onClick={() => navigate('/jobs')}
          className="mt-4 px-4 py-2 text-sm text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-500/10 transition-colors"
        >
          ← Go to Jobs
        </button>
      </div>
    );
  }

  // Success state
  if (result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center p-8">
        <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h2 className="text-2xl font-bold text-green-400">Application {result.status === 'sent' ? 'Sent' : 'Processed'}!</h2>
        <p className="text-slate-400 mt-2">{result.message}</p>
        <div className="mt-6 flex gap-3">
          <button onClick={() => navigate('/jobs')} className="px-4 py-2 text-sm text-slate-300 border border-[#1e293b] rounded-lg hover:bg-[#1a1f35] transition-colors">
            Back to Jobs
          </button>
          <button onClick={() => navigate('/dashboard')} className="px-4 py-2 text-sm text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-500/10 transition-colors">
            View Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/jobs')} className="p-2 text-slate-500 hover:text-slate-300 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Application Review</h1>
          <p className="text-slate-500 text-sm mt-1">
            Review before sending — {selectedJob.title} at {selectedJob.company}
          </p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-4" />
          <p className="text-slate-500">Tailoring your CV and preparing email...</p>
          <p className="text-slate-600 text-sm mt-1">This may take 30-60 seconds</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* HITL Content */}
      {applicationPreview && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Tailored CV Preview */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-blue-400" />
              Tailored CV Preview
            </h2>
            {applicationPreview.match_score && (
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="w-14 h-14 rounded-full match-ring flex items-center justify-center"
                  style={{ '--score': applicationPreview.match_score }}
                >
                  <div className="w-11 h-11 rounded-full bg-[#111827] flex items-center justify-center">
                    <span className="text-sm font-bold text-green-400">{Math.round(applicationPreview.match_score)}%</span>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-slate-200">Match Score</p>
                  <p className="text-xs text-slate-500">{selectedJob.company} — {selectedJob.title}</p>
                </div>
              </div>
            )}
            <div className="bg-[#0a0e1a] rounded-lg p-4 max-h-[500px] overflow-y-auto text-sm text-slate-300 leading-relaxed">
              {applicationPreview.tailored_cv ? (
                <pre className="whitespace-pre-wrap font-sans">
                  {typeof applicationPreview.tailored_cv === 'string'
                    ? applicationPreview.tailored_cv
                    : JSON.stringify(applicationPreview.tailored_cv, null, 2)}
                </pre>
              ) : (
                <p className="text-slate-500">No tailored CV available</p>
              )}
            </div>
          </div>

          {/* Right: Email Draft + Approval */}
          <div className="space-y-6">
            {/* Email Draft */}
            <div className="bg-[#111827] border border-[#1e293b] rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                  <Mail className="w-5 h-5 text-cyan-400" />
                  Email Draft
                </h2>
                <button
                  onClick={() => setEditMode(!editMode)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 border border-[#1e293b] rounded-lg hover:text-blue-400 hover:border-blue-500/30 transition-colors"
                >
                  <Edit3 className="w-3 h-3" />
                  {editMode ? 'Preview' : 'Edit'}
                </button>
              </div>

              {applicationPreview.hr_email && (
                <div className="mb-3 text-xs text-slate-500">
                  To: <span className="text-slate-300">{applicationPreview.hr_email}</span>
                </div>
              )}

              {editMode ? (
                <textarea
                  value={emailDraft}
                  onChange={(e) => setEmailDraft(e.target.value)}
                  className="w-full h-64 bg-[#0a0e1a] border border-[#1e293b] rounded-lg p-4 text-sm text-slate-300 resize-none focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              ) : (
                <div className="bg-[#0a0e1a] rounded-lg p-4 max-h-64 overflow-y-auto text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {emailDraft || 'No email draft available'}
                </div>
              )}
            </div>

            {/* HITL Approval Gate */}
            <div className="bg-[#111827] border border-amber-500/20 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-amber-400 mb-4 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5" />
                Human-in-the-Loop Approval
              </h2>
              <label className="flex items-start gap-3 cursor-pointer mb-4">
                <input
                  type="checkbox"
                  checked={approved}
                  onChange={(e) => setApproved(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-[#0a0e1a]"
                />
                <span className="text-sm text-slate-300">
                  I have reviewed the tailored CV and email draft. I approve sending this application.
                </span>
              </label>

              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={!approved || sending}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-semibold rounded-xl disabled:opacity-40 disabled:cursor-not-allowed hover:from-green-600 hover:to-emerald-700 transition-all glow-green"
                >
                  {sending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  {sending ? 'Sending...' : 'Approve & Send'}
                </button>
                <button
                  onClick={handleReject}
                  className="px-4 py-3 text-red-400 border border-red-500/20 rounded-xl hover:bg-red-500/10 transition-colors flex items-center gap-2"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
