import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import useAppStore from '../store/appStore';
import { uploadCV } from '../services/api';

export default function CVUpload() {
  const navigate = useNavigate();
  const { setParsedCV, parsedCV, isUploading, setUploading } = useAppStore();
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      setError('Please upload a PDF or DOCX file.');
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const result = await uploadCV(file);
      setParsedCV(result.parsed_cv, result.cv_id);
      setUploadResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Is the backend running?');
    } finally {
      setUploading(false);
    }
  }, [setParsedCV, setUploading]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const onFileSelect = (e) => handleFile(e.target.files[0]);

  return (
    <div className="min-h-screen p-8 flex flex-col items-center justify-center">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          HirePilot AI
        </h1>
        <p className="text-slate-400 mt-2 text-lg">Upload your CV to get started</p>
      </div>

      {/* Upload Zone */}
      {!uploadResult ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`relative w-full max-w-lg border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer ${
            dragOver
              ? 'border-blue-400 bg-blue-500/10 glow-blue'
              : 'border-[#1e293b] bg-[#111827] hover:border-blue-500/50 hover:bg-[#1a1f35]'
          }`}
        >
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={onFileSelect}
            className="absolute inset-0 opacity-0 cursor-pointer"
            disabled={isUploading}
          />
          {isUploading ? (
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
              <p className="text-blue-400 font-medium">Parsing your CV with AI...</p>
              <p className="text-slate-500 text-sm">This may take 15-30 seconds</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center">
                <Upload className="w-8 h-8 text-blue-400" />
              </div>
              <div>
                <p className="text-lg font-medium text-slate-200">
                  Drag & drop your CV here
                </p>
                <p className="text-slate-500 mt-1">or click to browse — PDF or DOCX</p>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Success Result */
        <div className="w-full max-w-2xl bg-[#111827] border border-[#1e293b] rounded-2xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <CheckCircle className="w-6 h-6 text-green-400" />
            <h2 className="text-xl font-semibold text-green-400">CV Parsed Successfully</h2>
          </div>

          {/* Profile Summary */}
          <div className="space-y-4">
            <ProfileField
              label="Name"
              value={uploadResult.parsed_cv?.contact_info?.name}
            />
            <ProfileField
              label="Email"
              value={uploadResult.parsed_cv?.contact_info?.email}
            />
            <ProfileField
              label="Phone"
              value={uploadResult.parsed_cv?.contact_info?.phone}
            />
            <ProfileField
              label="Skills"
              value={
                uploadResult.parsed_cv?.skills
                  ? `${uploadResult.skills_count} skills detected`
                  : null
              }
            />
            {uploadResult.parsed_cv?.skills?.technical_skills && (
              <div className="flex flex-wrap gap-2 mt-2">
                {uploadResult.parsed_cv.skills.technical_skills.slice(0, 12).map((s, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full"
                  >
                    {s}
                  </span>
                ))}
                {uploadResult.parsed_cv.skills.technical_skills.length > 12 && (
                  <span className="px-2 py-1 text-xs text-slate-500">
                    +{uploadResult.parsed_cv.skills.technical_skills.length - 12} more
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Action Button */}
          <button
            onClick={() => navigate('/chat')}
            className="mt-8 w-full py-3 px-6 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-cyan-600 transition-all duration-200 glow-blue"
          >
            Continue to AI Chat →
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mt-4 flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 max-w-lg">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}
    </div>
  );
}

function ProfileField({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-slate-500 w-20">{label}</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  );
}
