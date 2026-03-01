import { useState } from 'react';
import { Mail, CheckCircle, XCircle, Edit3, Loader2 } from 'lucide-react';
import { approveApplication } from '../services/api';
import useAppStore from '../store/appStore';

export default function EmailApprovalCard({ emailDraft, sessionId, onResult }) {
  const [body, setBody] = useState(emailDraft || '');
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // 'sent' | 'rejected' | null

  const handleApprove = async () => {
    setLoading(true);
    try {
      const res = await approveApplication(sessionId, body, true);
      setResult('sent');
      onResult?.({ status: 'sent', message: res.message });
    } catch (err) {
      onResult?.({ status: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await approveApplication(sessionId, body, false);
      setResult('rejected');
      onResult?.({ status: 'rejected', message: 'Application rejected.' });
    } catch (err) {
      onResult?.({ status: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  if (result === 'sent') {
    return (
      <div className="border border-green-500/30 bg-green-500/5 rounded-xl p-4 flex items-center gap-3">
        <CheckCircle className="w-5 h-5 text-green-400" />
        <span className="text-sm text-green-300">Application sent successfully!</span>
      </div>
    );
  }

  if (result === 'rejected') {
    return (
      <div className="border border-red-500/30 bg-red-500/5 rounded-xl p-4 flex items-center gap-3">
        <XCircle className="w-5 h-5 text-red-400" />
        <span className="text-sm text-red-300">Application rejected.</span>
      </div>
    );
  }

  return (
    <div className="border border-cyan-500/30 bg-[#0f1a2e] rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Mail className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-semibold text-cyan-300">Email Draft — Review & Approve</span>
      </div>

      {/* Email Body */}
      {editing ? (
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          className="w-full bg-[#1a1f35] border border-[#1e293b] rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 resize-none"
        />
      ) : (
        <div className="bg-[#1a1f35] border border-[#1e293b] rounded-lg px-3 py-2 text-sm text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
          {body}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => setEditing(!editing)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 border border-[#1e293b] rounded-lg hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
        >
          <Edit3 className="w-3 h-3" />
          {editing ? 'Preview' : 'Edit'}
        </button>

        <button
          onClick={handleApprove}
          disabled={loading}
          className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50 transition-colors"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
          Approve & Send
        </button>

        <button
          onClick={handleReject}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 disabled:opacity-50 transition-colors"
        >
          <XCircle className="w-3 h-3" />
          Reject
        </button>
      </div>
    </div>
  );
}
