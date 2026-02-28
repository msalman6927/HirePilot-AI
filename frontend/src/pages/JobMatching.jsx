import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, ExternalLink, Star, Loader2, RefreshCw, Search } from 'lucide-react';
import useAppStore from '../store/appStore';
import { getJobs } from '../services/api';

export default function JobMatching() {
  const navigate = useNavigate();
  const { jobs, setJobs, setSelectedJob, sessionId } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJobs(sessionId);
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobs.length === 0) fetchJobs();
  }, []);

  const filtered = jobs.filter((j) => {
    if (!filter) return true;
    const q = filter.toLowerCase();
    return (
      j.title?.toLowerCase().includes(q) ||
      j.company?.toLowerCase().includes(q) ||
      j.location?.toLowerCase().includes(q)
    );
  });

  const handleSelect = (job) => {
    setSelectedJob(job);
    navigate('/apply');
  };

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Job Matching</h1>
          <p className="text-slate-500 mt-1">
            {jobs.length} jobs found — select one to apply
          </p>
        </div>
        <button
          onClick={fetchJobs}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-[#1a1f35] border border-[#1e293b] rounded-xl text-sm text-slate-300 hover:border-blue-500/30 hover:text-blue-400 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Search Filter */}
      <div className="relative mb-6 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by title, company, or location..."
          className="w-full pl-10 pr-4 py-2.5 bg-[#1a1f35] border border-[#1e293b] rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && jobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-4" />
          <p className="text-slate-500">Loading jobs...</p>
        </div>
      )}

      {/* Empty */}
      {!loading && jobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Briefcase className="w-12 h-12 text-slate-700 mb-4" />
          <p className="text-slate-500 text-lg">No jobs yet</p>
          <p className="text-slate-600 text-sm mt-1">
            Go to Chat and ask: "Find Python developer jobs in Lahore"
          </p>
        </div>
      )}

      {/* Job Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((job, idx) => (
          <JobCard key={job.id || idx} job={job} rank={idx} onSelect={handleSelect} />
        ))}
      </div>
    </div>
  );
}

function JobCard({ job, rank, onSelect }) {
  const score = job.match_score || 0;
  const isBest = rank < 3 && score > 0;

  return (
    <div className={`relative bg-[#111827] border rounded-xl p-5 transition-all duration-200 hover:border-blue-500/40 hover:bg-[#1a1f35] ${
      isBest ? 'border-green-500/30' : 'border-[#1e293b]'
    }`}>
      {/* Best Match Badge */}
      {isBest && (
        <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <Star className="w-3 h-3 text-green-400" />
          <span className="text-[10px] font-semibold text-green-400">BEST MATCH</span>
        </div>
      )}

      {/* Match Score Ring */}
      {score > 0 && (
        <div className="mb-3 flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-full match-ring flex items-center justify-center"
            style={{ '--score': score }}
          >
            <div className="w-9 h-9 rounded-full bg-[#111827] flex items-center justify-center">
              <span className="text-xs font-bold text-green-400">{Math.round(score)}%</span>
            </div>
          </div>
          <span className="text-xs text-slate-500">Match Score</span>
        </div>
      )}

      {/* Content */}
      <h3 className="text-base font-semibold text-slate-100 mb-1 line-clamp-2 pr-16">
        {job.title}
      </h3>
      <p className="text-sm text-blue-400 mb-2">{job.company}</p>

      <div className="flex items-center gap-4 text-xs text-slate-500 mb-3">
        {job.location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" /> {job.location}
          </span>
        )}
        {job.platform && (
          <span className="capitalize px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">
            {job.platform}
          </span>
        )}
      </div>

      {job.description && (
        <p className="text-xs text-slate-400 line-clamp-3 mb-4">{job.description}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onSelect(job)}
          className="flex-1 py-2 px-4 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-sm font-medium hover:bg-blue-500/20 transition-colors"
        >
          Select & Apply
        </button>
        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
    </div>
  );
}
