import React, { useState } from 'react';
import { ArrowLeft, ChevronRight, Upload, FileText, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';
import { uploadNotes } from '../services/api';
import { NotesUploadResponse } from '../types/api';

interface Props {
  courseCode: string;
  scheme: string;
  notesChoice: 'upload' | 'none';
  uploadedNotes: NotesUploadResponse | null;
  onChoiceChange: (choice: 'upload' | 'none') => void;
  onNotesUploaded: (notes: NotesUploadResponse | null) => void;
  onNext: () => void;
  onBack: () => void;
  isGeneratingPlan: boolean;
}

export const Step3Notes: React.FC<Props> = ({
  courseCode,
  scheme,
  notesChoice,
  uploadedNotes,
  onChoiceChange,
  onNotesUploaded,
  onNext,
  onBack,
  isGeneratingPlan,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMsg('Only PDF files are supported.');
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setErrorMsg('File size exceeds the 20MB limit.');
      return;
    }

    setSelectedFile(file);
    setErrorMsg(null);
    setUploading(true);

    try {
      const res = await uploadNotes(file, courseCode, scheme);
      onNotesUploaded(res);
      onChoiceChange('upload');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to upload and extract notes PDF.');
      onNotesUploaded(null);
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveNotes = () => {
    setSelectedFile(null);
    onNotesUploaded(null);
    setErrorMsg(null);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 tracking-tight">Study Material & Notes</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Choose whether to upload faculty notes or generate content from verified VTU web sources.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Option A: Upload Notes */}
        <label
          onClick={() => onChoiceChange('upload')}
          className={`relative border rounded-lg p-4 cursor-pointer flex flex-col justify-between transition-all ${
            notesChoice === 'upload'
              ? 'border-indigo-600 bg-indigo-50/20 ring-1 ring-indigo-600'
              : 'border-slate-200 hover:border-slate-300 bg-white'
          }`}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                Upload Faculty Notes
              </span>
              <input
                type="radio"
                name="notesChoice"
                checked={notesChoice === 'upload'}
                onChange={() => onChoiceChange('upload')}
                className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
              />
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Upload class notes (PDF up to 20MB). Answers will be extracted and grounded strictly in your notes.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100">
            {uploadedNotes ? (
              <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded border border-slate-200 text-xs">
                <div className="min-w-0 pr-2">
                  <span className="font-medium text-slate-900 truncate block">
                    {uploadedNotes.filename}
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    {uploadedNotes.pages_count} pages • {(uploadedNotes.file_size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveNotes();
                  }}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  id="notes-upload-input"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <label
                  htmlFor="notes-upload-input"
                  className={`w-full py-2 px-3 border border-dashed rounded-md flex items-center justify-center gap-2 text-xs font-medium cursor-pointer transition-colors ${
                    uploading
                      ? 'bg-slate-50 text-slate-400 border-slate-200'
                      : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Extracting PDF text...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5 text-slate-500" />
                      <span>Select PDF File</span>
                    </>
                  )}
                </label>
              </div>
            )}
          </div>
        </label>

        {/* Option B: Continue without Uploading */}
        <label
          onClick={() => onChoiceChange('none')}
          className={`relative border rounded-lg p-4 cursor-pointer flex flex-col justify-between transition-all ${
            notesChoice === 'none'
              ? 'border-indigo-600 bg-indigo-50/20 ring-1 ring-indigo-600'
              : 'border-slate-200 hover:border-slate-300 bg-white'
          }`}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-slate-500" />
                Continue Without Upload
              </span>
              <input
                type="radio"
                name="notesChoice"
                checked={notesChoice === 'none'}
                onChange={() => onChoiceChange('none')}
                className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
              />
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              The engine searches open VTU syllabus repositories for {courseCode}. Answers will cite the source URLs.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100">
            <span className="text-[11px] text-slate-400 block italic">
              Online notes with university citations
            </span>
          </div>
        </label>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="flex items-start gap-2 bg-rose-50 border border-rose-200 p-3 rounded-md text-xs text-rose-700">
          <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Attribution notice */}
      {notesChoice === 'none' && (
        <div className="bg-slate-50 p-3 rounded-md border border-slate-200 text-xs text-slate-600">
          <p className="font-medium text-slate-800 mb-0.5">Note on Generated Answers:</p>
          <p className="text-[11px] text-slate-500">
            Answers are synthesized from verified VTU web pages and curriculum references. Always cross-check with your prescribed textbook or course faculty.
          </p>
        </div>
      )}

      <div className="pt-2 flex justify-between items-center">
        <button
          type="button"
          onClick={onBack}
          disabled={isGeneratingPlan}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back</span>
        </button>

        <button
          type="button"
          onClick={onNext}
          disabled={isGeneratingPlan || (notesChoice === 'upload' && !uploadedNotes)}
          className={`inline-flex items-center gap-2 px-5 py-2 rounded-md text-xs font-medium transition-all shadow-xs ${
            isGeneratingPlan || (notesChoice === 'upload' && !uploadedNotes)
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {isGeneratingPlan ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Building Timetable...</span>
            </>
          ) : (
            <>
              <span>Generate Timetable</span>
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
