import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, Briefcase, Zap } from 'lucide-react';
import useAppStore from '../store/appStore';
import { sendMessage } from '../services/api';
import ReactMarkdown from 'react-markdown';
import EmailApprovalCard from '../components/EmailApprovalCard';

export default function Chatbot() {
  const {
    chatMessages, addChatMessage,
    sessionId, parsedCV,
    isAgentRunning, setAgentRunning,
    setJobs,
  } = useAppStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isAgentRunning) return;
    setInput('');
    addChatMessage({ role: 'user', content: text });
    setAgentRunning(true);

    try {
      const res = await sendMessage(text, sessionId, {});
      addChatMessage({
        role: 'assistant',
        content: res.response || 'No response from agent.',
        intent: res.detected_intent,
        logs: res.agent_logs,
        email_draft: res.email_draft || null,
      });
      // If jobs came back from the agent, save them
      if (res.found_jobs && res.found_jobs.length > 0) {
        setJobs(res.found_jobs);
      }
    } catch (err) {
      addChatMessage({
        role: 'assistant',
        content: `Error: ${err.response?.data?.detail || err.message}`,
      });
    } finally {
      setAgentRunning(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-screen flex">
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="px-6 py-4 border-b border-[#1e293b] bg-[#0d1225]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-100">HirePilot AI Chat</h1>
              <p className="text-xs text-slate-500">
                {isAgentRunning ? (
                  <span className="text-cyan-400 animate-pulse-neon">Agents working...</span>
                ) : (
                  'Ask me to find jobs, tailor your CV, or apply'
                )}
              </p>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {chatMessages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Zap className="w-12 h-12 text-blue-400/30 mb-4" />
              <p className="text-slate-500 text-lg">Start a conversation</p>
              <div className="mt-4 flex flex-wrap gap-2 justify-center max-w-md">
                {[
                  'Find Python developer jobs in Lahore',
                  'Show me remote React jobs',
                  'Prepare me for a data science interview',
                ].map((s) => (
                  <button
                    key={s}
                    onClick={() => { setInput(s); inputRef.current?.focus(); }}
                    className="px-3 py-1.5 text-sm text-slate-400 bg-[#1a1f35] border border-[#1e293b] rounded-lg hover:text-blue-400 hover:border-blue-500/30 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {chatMessages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-cyan-400" />
                </div>
              )}
              <div
                className={`max-w-[70%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user' ? 'chat-user' : 'chat-ai'
                }`}
              >
                <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
                  {msg.content}
                </ReactMarkdown>
                {msg.intent && (
                  <div className="mt-2 flex items-center gap-1.5">
                    <Briefcase className="w-3 h-3 text-blue-400" />
                    <span className="text-xs text-blue-400">Intent: {msg.intent}</span>
                  </div>
                )}
                {msg.email_draft && (
                  <div className="mt-3">
                    <EmailApprovalCard
                      emailDraft={msg.email_draft}
                      sessionId={sessionId}
                      onResult={(r) => {
                        addChatMessage({
                          role: 'assistant',
                          content: r.message || `Application ${r.status}.`,
                        });
                      }}
                    />
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4 text-blue-400" />
                </div>
              )}
            </div>
          ))}

          {isAgentRunning && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="chat-ai rounded-xl px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                <span className="text-sm text-cyan-400">Agents processing your request...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-[#1e293b] bg-[#0d1225]">
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              rows={1}
              className="flex-1 bg-[#1a1f35] border border-[#1e293b] rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isAgentRunning}
              className="w-11 h-11 flex items-center justify-center rounded-xl bg-blue-500 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel: CV Profile */}
      <aside className="w-80 border-l border-[#1e293b] bg-[#0d1225] overflow-y-auto hidden lg:block">
        <div className="p-5">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            Your Profile
          </h2>
          {parsedCV ? (
            <div className="space-y-4">
              <ProfileSection label="Name" value={parsedCV.contact_info?.name} />
              <ProfileSection label="Email" value={parsedCV.contact_info?.email} />
              <ProfileSection label="Phone" value={parsedCV.contact_info?.phone} />
              <ProfileSection label="Location" value={parsedCV.contact_info?.location} />
              {parsedCV.professional_summary && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Summary</p>
                  <p className="text-xs text-slate-300 leading-relaxed line-clamp-4">
                    {parsedCV.professional_summary}
                  </p>
                </div>
              )}
              {parsedCV.skills?.technical_skills && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Technical Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {parsedCV.skills.technical_skills.slice(0, 15).map((s, i) => (
                      <span key={i} className="px-2 py-0.5 text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {parsedCV.work_experience && parsedCV.work_experience.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Experience</p>
                  {parsedCV.work_experience.slice(0, 3).map((exp, i) => (
                    <div key={i} className="mb-2 p-2 bg-[#1a1f35] rounded-lg">
                      <p className="text-xs font-medium text-slate-200">{exp.title || exp.job_title}</p>
                      <p className="text-[10px] text-slate-500">{exp.company} — {exp.duration || exp.dates}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-10">
              <p className="text-slate-500 text-sm">No CV uploaded yet</p>
              <p className="text-slate-600 text-xs mt-1">Upload on the CV page first</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function ProfileSection({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm text-slate-200">{value}</p>
    </div>
  );
}
