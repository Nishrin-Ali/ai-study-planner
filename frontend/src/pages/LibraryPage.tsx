import React, { useState, useEffect } from 'react';
import { getPapers, uploadPaper, startPaperFetch, getPaperFetchProgress } from '../services/api';
import { QuestionPaperSummary, FetchJobProgress } from '../types/api';
import { Library, Upload, Search, ExternalLink, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-react';

export const LibraryPage: React.FC = () => {
  const [papers, setPapers] = useState<QuestionPaperSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchCode, setSearchCode] = useState('BCS304');
  const [searchScheme, setSearchScheme] = useState('2022');

  // Manual Upload Form State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [upCourseCode, setUpCourseCode] = useState('BCS304');
  const [upScheme, setUpScheme] = useState('2022');
  const [upBranch, setUpBranch] = useState('CSE');
  const [upSemester, setUpSemester] = useState(3);
  const [upSession, setUpSession] = useState('Jan/Feb 2024');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Background Web Discovery State
  const [isFetchingWeb, setIsFetchingWeb] = useState(false);
  const [fetchProgress, setFetchProgress] = useState<FetchJobProgress | null>(null);

  const loadPapers = async () => {
    setLoading(true);
    try {
      const data = await getPapers(searchCode, searchScheme);
      setPapers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPapers();
  }, [searchCode, searchScheme]);

  const handleManualUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a PDF question paper.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await uploadPaper(
        uploadFile,
        upCourseCode,
        upScheme,
        upBranch,
        upSemester,
        upSession
      );
      setUploadSuccess(`Successfully uploaded and validated ${uploadFile.name}`);
      setUploadFile(null);
      loadPapers();
    } catch (err: any) {
      setUploadError(err.message || 'Validation failed. Ensure course code and exam session match.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTriggerWebFetch = async () => {
    setIsFetchingWeb(true);
    try {
      const startRes = await startPaperFetch(searchCode, 'Course Subject', searchScheme);
      const jobId = startRes.job_id;

      const timer = setInterval(async () => {
        try {
          const prog = await getPaperFetchProgress(jobId);
          setFetchProgress(prog);

          if (prog.status === 'completed' || prog.status === 'failed') {
            clearInterval(timer);
            setIsFetchingWeb(false);
            loadPapers();
          }
        } catch (e) {
          clearInterval(timer);
          setIsFetchingWeb(false);
        }
      }, 1000);
    } catch (e) {
      setIsFetchingWeb(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
          <Library className="w-5 h-5 text-indigo-600" />
          VTU Question Papers Library
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Explore cached university exam papers, trigger web discovery, or upload question papers manually.
        </p>
      </div>

      {/* Discovery & Search Controls */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 max-w-sm">
            <input
              type="text"
              value={searchCode}
              onChange={(e) => setSearchCode(e.target.value.toUpperCase())}
              placeholder="Course Code (e.g. BCS304)"
              className="bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 flex-1"
            />
            <select
              value={searchScheme}
              onChange={(e) => setSearchScheme(e.target.value)}
              className="bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="2022">2022 Scheme</option>
              <option value="2021">2021 Scheme</option>
              <option value="2018">2018 Scheme</option>
            </select>
          </div>

          <button
            onClick={handleTriggerWebFetch}
            disabled={isFetchingWeb}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors self-start sm:self-auto"
          >
            {isFetchingWeb ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Searching Web Repositories...</span>
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                <span>Fetch Papers from Web</span>
              </>
            )}
          </button>
        </div>

        {/* Live progress indicator */}
        {isFetchingWeb && fetchProgress && (
          <div className="pt-2 border-t border-slate-100">
            <div className="flex justify-between text-xs text-slate-600 mb-1">
              <span>{fetchProgress.message}</span>
              <span className="font-mono">{fetchProgress.progress_pct}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5">
              <div
                className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${fetchProgress.progress_pct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Cached Papers Table */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-xs">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
          <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Cached Papers for {searchCode} ({papers.length})
          </h2>
          <span className="text-[11px] text-slate-500 font-mono">
            {papers.length >= 2 ? 'Reliable repetition data available' : 'Needs >= 2 papers for analysis'}
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-600" />
            Loading papers...
          </div>
        ) : papers.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-xs text-slate-600">No cached question papers found for {searchCode}.</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Click &quot;Fetch Papers from Web&quot; or manually upload a question paper PDF below.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-medium">
                <tr>
                  <th className="px-5 py-2.5">Exam Session</th>
                  <th className="px-5 py-2.5">Scheme</th>
                  <th className="px-5 py-2.5">Status</th>
                  <th className="px-5 py-2.5">Actions & Source</th>
                  <th className="px-5 py-2.5">Questions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {papers.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-900">{p.exam_session}</td>
                    <td className="px-5 py-3 text-slate-600">{p.scheme} Scheme</td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3" /> Validated
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      <div className="flex items-center gap-2.5">
                        {p.has_file !== false && (
                          <a
                            href={p.file_url || `/api/papers/${p.id}/file`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>Open paper</span>
                          </a>
                        )}
                        {p.source_url && (
                          <a
                            href={p.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-slate-500 hover:text-indigo-600 hover:underline text-xs"
                          >
                            <span>Original source</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-700 font-mono">
                      {p.questions_count || '10'} items
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Manual Upload Section */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Upload className="w-4 h-4 text-indigo-600" />
            Manual Question Paper Upload
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload an authentic VTU question paper PDF to enrich local repetition clustering.
          </p>
        </div>

        <form onSubmit={handleManualUpload} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Course Code</label>
            <input
              type="text"
              required
              value={upCourseCode}
              onChange={(e) => setUpCourseCode(e.target.value.toUpperCase())}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Scheme</label>
            <select
              value={upScheme}
              onChange={(e) => setUpScheme(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="2022">2022</option>
              <option value="2021">2021</option>
              <option value="2018">2018</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Exam Session</label>
            <input
              type="text"
              required
              placeholder="e.g. Jan/Feb 2024"
              value={upSession}
              onChange={(e) => setUpSession(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="sm:col-span-3">
            <label className="block text-xs font-medium text-slate-700 mb-1">PDF File</label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              required
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="block w-full text-xs text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            />
          </div>

          {uploadSuccess && (
            <div className="sm:col-span-3 flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-2 rounded-md text-xs">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          {uploadError && (
            <div className="sm:col-span-3 flex items-center gap-2 bg-rose-50 border border-rose-200 text-rose-800 px-3 py-2 rounded-md text-xs">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          <div className="sm:col-span-3 flex justify-end">
            <button
              type="submit"
              disabled={isUploading || !uploadFile}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium transition-colors ${
                isUploading || !uploadFile
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Validating & Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload Question Paper</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
