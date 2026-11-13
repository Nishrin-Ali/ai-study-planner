import React, { useState } from 'react';
import { ArrowLeft, ChevronRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { startPaperFetch, getPaperFetchProgress, getImportantQuestions } from '../services/api';
import { ImportantQuestionsResponse, FetchJobProgress } from '../types/api';

interface Props {
  courseCode: string;
  courseTitle: string;
  scheme: string;
  data: {
    numModules: number;
    numDays: number;
    onlyImportantQuestions: boolean;
  };
  onChange: (field: string, val: any) => void;
  onNext: () => void;
  onBack: () => void;
  onImportantQuestionsLoaded?: (data: ImportantQuestionsResponse) => void;
}

export const Step2Options: React.FC<Props> = ({
  courseCode,
  courseTitle,
  scheme,
  data,
  onChange,
  onNext,
  onBack,
  onImportantQuestionsLoaded,
}) => {
  const [fetchProgress, setFetchProgress] = useState<FetchJobProgress | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [iqResult, setIqResult] = useState<ImportantQuestionsResponse | null>(null);

  const modulesList = [1, 2, 3, 4, 5];
  const daysList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  const handleImportantQuestionsToggle = async (checked: boolean) => {
    onChange('onlyImportantQuestions', checked);
    if (!checked) return;

    // Check papers & run fetch job
    setIsFetching(true);
    try {
      const selectedMods = Array.from({ length: data.numModules }, (_, i) => i + 1);
      const startRes = await startPaperFetch(courseCode, courseTitle, scheme);
      const jobId = startRes.job_id;

      // Poll progress
      const pollTimer = setInterval(async () => {
        try {
          const prog = await getPaperFetchProgress(jobId);
          setFetchProgress(prog);

          if (prog.status === 'completed' || prog.status === 'failed') {
            clearInterval(pollTimer);
            setIsFetching(false);

            // Fetch important questions
            const iq = await getImportantQuestions(courseCode, scheme, selectedMods);
            setIqResult(iq);
            if (onImportantQuestionsLoaded) onImportantQuestionsLoaded(iq);
          }
        } catch (e) {
          clearInterval(pollTimer);
          setIsFetching(false);
        }
      }, 1000);
    } catch (e) {
      setIsFetching(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 tracking-tight">Plan Configuration</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Select workload scope and available preparation duration.
        </p>
      </div>

      {/* Number of Modules (1-5) */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs font-medium text-slate-700">Number of Modules to Cover</label>
          <span className="text-xs font-semibold text-indigo-600">
            {data.numModules} {data.numModules === 1 ? 'Module' : 'Modules'}
          </span>
        </div>
        <div className="grid grid-cols-5 gap-2">
          {modulesList.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => onChange('numModules', m)}
              className={`py-2 text-xs font-medium rounded-md border text-center transition-all ${
                data.numModules === m
                  ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              M1–{m}
            </button>
          ))}
        </div>
      </div>

      {/* Number of Days (1-10) */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs font-medium text-slate-700">Days Available for Study</label>
          <span className="text-xs font-semibold text-indigo-600">
            {data.numDays} {data.numDays === 1 ? 'Day' : 'Days'}
          </span>
        </div>
        <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
          {daysList.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => onChange('numDays', d)}
              className={`py-2 text-xs font-medium rounded-md border text-center transition-all ${
                data.numDays === d
                  ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-xs'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Only Important Questions Checkbox */}
      <div className="border border-slate-200 rounded-md p-4 bg-slate-50/50 space-y-3">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={data.onlyImportantQuestions}
            onChange={(e) => handleImportantQuestionsToggle(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <div>
            <span className="text-xs font-semibold text-slate-900 block">
              Only Important Questions (VTU Question Paper Analysis)
            </span>
            <span className="text-[11px] text-slate-500 leading-relaxed block mt-0.5">
              Discovers past semester question papers, filters authentic university questions, and clusters topics by repetition frequency.
            </span>
          </div>
        </label>

        {/* Live Fetching Progress Strip */}
        {isFetching && (
          <div className="pt-2 border-t border-slate-200/80">
            <div className="flex items-center justify-between text-xs text-slate-700 mb-1.5">
              <span className="inline-flex items-center gap-1.5 font-medium">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                {fetchProgress ? fetchProgress.message : 'Initiating question paper search...'}
              </span>
              <span className="font-mono text-slate-500">{fetchProgress?.progress_pct || 10}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${fetchProgress?.progress_pct || 15}%` }}
              />
            </div>
          </div>
        )}

        {/* Repetition Analysis Feedback */}
        {iqResult && (
          <div className="pt-2 border-t border-slate-200/80">
            {iqResult.is_reliable ? (
              <div className="flex items-start gap-2 text-xs text-emerald-800 bg-emerald-50/80 p-2.5 rounded border border-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">{iqResult.message}</p>
                  <p className="text-[11px] text-emerald-700 mt-0.5">
                    Sessions analyzed: {iqResult.exam_sessions.join(', ')}.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">{iqResult.message}</p>
                  <p className="text-[11px] text-amber-700 mt-0.5">
                    You can upload past question papers manually in the Library to enrich repetition counts.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="pt-2 flex justify-between items-center">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back</span>
        </button>

        <button
          type="button"
          onClick={onNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-all shadow-xs"
        >
          <span>Continue to Notes</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
