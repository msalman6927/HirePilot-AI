import { useState, useEffect } from 'react';
import { getJobs, getInterviewPrep } from '../services/api';
import {
  GraduationCap,
  Brain,
  AlertTriangle,
  Building2,
  DollarSign,
  Rocket,
  ChevronDown,
  ChevronUp,
  Loader2,
  Briefcase,
  CheckCircle,
  Star,
} from 'lucide-react';

// ── Accordion Section ─────────────────────────────────────────
function AccordionSection({ title, icon: Icon, color, count, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[#1e293b] rounded-xl overflow-hidden mb-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 bg-[#0d1225] hover:bg-[#111a33] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${color}`}>
            <Icon className="w-4 h-4" />
          </div>
          <span className="text-sm font-semibold text-slate-200">{title}</span>
          {count !== undefined && (
            <span className="text-xs text-slate-500 bg-[#1a1f35] px-2 py-0.5 rounded-full">{count}</span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {open && <div className="px-5 py-4 bg-[#0a0e1a] border-t border-[#1e293b]">{children}</div>}
    </div>
  );
}

// ── Difficulty Badge ──────────────────────────────────────────
function DifficultyBadge({ level }) {
  const styles = {
    easy: 'bg-green-500/20 text-green-400',
    medium: 'bg-yellow-500/20 text-yellow-400',
    hard: 'bg-red-500/20 text-red-400',
  };
  return (
    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${styles[level] || styles.medium}`}>
      {level}
    </span>
  );
}

// ── Importance Badge ──────────────────────────────────────────
function ImportanceBadge({ level }) {
  const styles = {
    critical: 'bg-red-500/20 text-red-400',
    important: 'bg-yellow-500/20 text-yellow-400',
    nice_to_have: 'bg-blue-500/20 text-blue-400',
  };
  return (
    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${styles[level] || styles.important}`}>
      {level?.replace('_', ' ')}
    </span>
  );
}

// ── Main Page ─────────────────────────────────────────────────
export default function InterviewPrep() {
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [prep, setPrep] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [error, setError] = useState('');

  // Load saved jobs on mount
  useEffect(() => {
    (async () => {
      try {
        const data = await getJobs();
        setJobs(data || []);
      } catch {
        setJobs([]);
      } finally {
        setLoadingJobs(false);
      }
    })();
  }, []);

  // Generate prep for selected job
  async function handleGenerate() {
    if (!selectedJobId) return;
    setLoading(true);
    setError('');
    setPrep(null);
    try {
      const data = await getInterviewPrep(selectedJobId);
      setPrep(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to generate interview prep. Try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <GraduationCap className="w-6 h-6 text-purple-400" />
          </div>
          Interview Preparation
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Select a saved job and generate AI-powered interview prep material with technical questions, behavioral STAR answers, skill gap analysis, and more.
        </p>
      </div>

      {/* Job Selector */}
      <div className="bg-[#0d1225] border border-[#1e293b] rounded-xl p-5 mb-6">
        <label className="block text-xs font-medium text-slate-400 mb-2">Select a Job</label>
        {loadingJobs ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-slate-500">No jobs found. Search for jobs first via the AI Chat.</p>
        ) : (
          <div className="flex gap-3">
            <select
              value={selectedJobId || ''}
              onChange={(e) => setSelectedJobId(Number(e.target.value))}
              className="flex-1 bg-[#0a0e1a] border border-[#1e293b] rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">-- Choose a job --</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} at {j.company} {j.match_score ? `(${Math.round(j.match_score)}% match)` : ''}
                </option>
              ))}
            </select>
            <button
              onClick={handleGenerate}
              disabled={!selectedJobId || loading}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
              {loading ? 'Generating...' : 'Generate Prep'}
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 text-sm text-red-400">{error}</div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          <p className="text-sm text-slate-400">Generating interview prep with AI... This may take 15-30 seconds.</p>
        </div>
      )}

      {/* Prep Results */}
      {prep && !loading && (
        <div className="space-y-1">
          {/* Title bar */}
          <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-xl p-5 mb-5">
            <div className="flex items-center gap-3">
              <Briefcase className="w-5 h-5 text-purple-400" />
              <div>
                <h2 className="text-lg font-bold text-white">{prep.job_title}</h2>
                <p className="text-sm text-slate-400">{prep.company}</p>
              </div>
            </div>
          </div>

          {/* Technical Questions */}
          <AccordionSection
            title="Technical Questions"
            icon={Brain}
            color="bg-blue-500/20 text-blue-400"
            count={prep.technical_questions?.length}
            defaultOpen={true}
          >
            <div className="space-y-4">
              {prep.technical_questions?.map((q, i) => (
                <div key={i} className="bg-[#111a33] rounded-lg p-4 border border-[#1e293b]">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm font-medium text-slate-200">
                      <span className="text-blue-400 mr-2">Q{i + 1}.</span>
                      {q.question}
                    </p>
                    <DifficultyBadge level={q.difficulty} />
                  </div>
                  <div className="mt-3 bg-[#0a0e1a] rounded-lg p-3 border border-[#1e293b]">
                    <p className="text-xs font-medium text-green-400 mb-1 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Model Answer
                    </p>
                    <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{q.model_answer}</p>
                  </div>
                </div>
              ))}
            </div>
          </AccordionSection>

          {/* Behavioral Questions (STAR) */}
          <AccordionSection
            title="Behavioral Questions (STAR)"
            icon={Star}
            color="bg-yellow-500/20 text-yellow-400"
            count={prep.behavioral_questions?.length}
          >
            <div className="space-y-4">
              {prep.behavioral_questions?.map((q, i) => (
                <div key={i} className="bg-[#111a33] rounded-lg p-4 border border-[#1e293b]">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm font-medium text-slate-200">
                      <span className="text-yellow-400 mr-2">Q{i + 1}.</span>
                      {q.question}
                    </p>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 font-bold uppercase">
                      {q.competency}
                    </span>
                  </div>
                  {q.star_answer && (
                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {['situation', 'task', 'action', 'result'].map((part) => (
                        <div key={part} className="bg-[#0a0e1a] rounded-lg p-3 border border-[#1e293b]">
                          <p className="text-[10px] font-bold text-yellow-400 uppercase mb-1">{part}</p>
                          <p className="text-xs text-slate-300 leading-relaxed">{q.star_answer[part]}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </AccordionSection>

          {/* Skill Gaps */}
          <AccordionSection
            title="Skill Gap Analysis"
            icon={AlertTriangle}
            color="bg-red-500/20 text-red-400"
            count={prep.skill_gaps?.length}
          >
            <div className="space-y-3">
              {prep.skill_gaps?.map((gap, i) => (
                <div key={i} className="flex items-start gap-4 bg-[#111a33] rounded-lg p-4 border border-[#1e293b]">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-slate-200">{gap.skill}</span>
                      <ImportanceBadge level={gap.importance} />
                    </div>
                    <p className="text-xs text-slate-400">
                      <span className="text-cyan-400 font-medium">Resource:</span> {gap.learning_resource}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      <span className="text-slate-400">Est. Time:</span> {gap.estimated_time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </AccordionSection>

          {/* Company Research */}
          <AccordionSection
            title="Company Research"
            icon={Building2}
            color="bg-cyan-500/20 text-cyan-400"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-bold text-cyan-400 uppercase mb-2">What to Know</h4>
                <ul className="space-y-2">
                  {prep.company_research?.what_to_know?.map((item, i) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs font-bold text-cyan-400 uppercase mb-2">Questions to Ask</h4>
                <ul className="space-y-2">
                  {prep.company_research?.questions_to_ask?.map((item, i) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </AccordionSection>

          {/* Salary Guidance */}
          <AccordionSection
            title="Salary Guidance"
            icon={DollarSign}
            color="bg-green-500/20 text-green-400"
          >
            <div>
              <p className="text-sm text-slate-200 mb-3">
                <span className="text-green-400 font-medium">Expected Range:</span>{' '}
                {prep.salary_guidance?.range || 'Not available'}
              </p>
              <h4 className="text-xs font-bold text-green-400 uppercase mb-2">Negotiation Tips</h4>
              <ul className="space-y-2">
                {prep.salary_guidance?.negotiation_tips?.map((tip, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">•</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          </AccordionSection>

          {/* Day One Tips */}
          <AccordionSection
            title="Day One Tips"
            icon={Rocket}
            color="bg-purple-500/20 text-purple-400"
            count={prep.day_one_tips?.length}
          >
            <ul className="space-y-2">
              {prep.day_one_tips?.map((tip, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                  <span className="text-purple-400 mt-0.5">{i + 1}.</span>
                  {tip}
                </li>
              ))}
            </ul>
          </AccordionSection>
        </div>
      )}

      {/* Empty State */}
      {!prep && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="p-4 rounded-2xl bg-purple-500/10">
            <GraduationCap className="w-10 h-10 text-purple-400/50" />
          </div>
          <p className="text-sm text-slate-500 text-center max-w-md">
            Select a job from the dropdown above and click "Generate Prep" to get AI-powered interview preparation material.
          </p>
        </div>
      )}
    </div>
  );
}
