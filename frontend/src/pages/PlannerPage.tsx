import React, { useState, useEffect } from 'react';
import { getCatalog, createStudyPlan, getStudyPlan } from '../services/api';
import { CatalogResponse, StudyPlanResponse, ImportantQuestionsResponse, NotesUploadResponse } from '../types/api';
import { Step1Academic } from '../components/Step1Academic';
import { Step2Options } from '../components/Step2Options';
import { Step3Notes } from '../components/Step3Notes';
import { Step4Timetable } from '../components/Step4Timetable';
import { Check } from 'lucide-react';

const STORAGE_KEY = 'vtu_study_planner_active_plan';

export const PlannerPage: React.FC = () => {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);

  // Step 1 Form Data
  const [academicData, setAcademicData] = useState({
    branch: 'CSE',
    year: 2,
    semester: 3,
    scheme: '2022',
    courseCode: 'BCS304',
    courseTitle: 'Data Structures and Applications',
  });

  // Step 2 Form Data
  const [planOptions, setPlanOptions] = useState({
    numModules: 3,
    numDays: 4,
    onlyImportantQuestions: false,
  });

  // Step 3 Form Data
  const [notesChoice, setNotesChoice] = useState<'upload' | 'none'>('none');
  const [uploadedNotes, setUploadedNotes] = useState<NotesUploadResponse | null>(null);

  // Step 4 Generated Timetable
  const [activePlan, setActivePlan] = useState<StudyPlanResponse | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    return null;
  });

  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);

  useEffect(() => {
    getCatalog()
      .then((data) => {
        setCatalog(data);
        setLoadingCatalog(false);
      })
      .catch((err) => {
        console.error('Error fetching catalog:', err);
        setLoadingCatalog(false);
      });
  }, []);

  useEffect(() => {
    if (activePlan) {
      setCurrentStep(4);
    }
  }, [activePlan]);

  const handleAcademicChange = (field: string, val: any) => {
    setAcademicData((prev) => ({ ...prev, [field]: val }));
  };

  const handleOptionsChange = (field: string, val: any) => {
    setPlanOptions((prev) => ({ ...prev, [field]: val }));
  };

  const handleGeneratePlan = async () => {
    setIsGeneratingPlan(true);
    try {
      const plan = await createStudyPlan({
        course_code: academicData.courseCode,
        course_title: academicData.courseTitle || academicData.courseCode,
        branch: academicData.branch,
        semester: academicData.semester,
        scheme: academicData.scheme,
        num_modules: planOptions.numModules,
        num_days: planOptions.numDays,
        only_important_questions: planOptions.onlyImportantQuestions,
        notes_id: notesChoice === 'upload' && uploadedNotes ? uploadedNotes.notes_id : null,
      });

      setActivePlan(plan);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
      setCurrentStep(4);
    } catch (err: any) {
      alert(`Error generating plan: ${err.message || 'Please check inputs and retry.'}`);
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  const handleResetPlan = () => {
    localStorage.removeItem(STORAGE_KEY);
    setActivePlan(null);
    setCurrentStep(1);
  };

  const steps = [
    { num: 1, label: 'Details' },
    { num: 2, label: 'Options' },
    { num: 3, label: 'Notes' },
    { num: 4, label: 'Timetable' },
  ];

  if (loadingCatalog) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Loading VTU Academic Catalog...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Slim Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between relative">
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-200 -z-10 -translate-y-1/2" />
          {steps.map((st) => (
            <div key={st.num} className="flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all ${
                  currentStep > st.num
                    ? 'bg-indigo-600 text-white'
                    : currentStep === st.num
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-50'
                    : 'bg-white border border-slate-300 text-slate-400'
                }`}
              >
                {currentStep > st.num ? <Check className="w-3.5 h-3.5" /> : st.num}
              </div>
              <span
                className={`text-[11px] font-medium mt-1.5 ${
                  currentStep >= st.num ? 'text-slate-900' : 'text-slate-400'
                }`}
              >
                {st.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Step Components */}
      {currentStep === 1 && catalog && (
        <Step1Academic
          catalog={catalog}
          data={academicData}
          onChange={handleAcademicChange}
          onNext={() => setCurrentStep(2)}
        />
      )}

      {currentStep === 2 && (
        <Step2Options
          courseCode={academicData.courseCode}
          courseTitle={academicData.courseTitle}
          scheme={academicData.scheme}
          data={planOptions}
          onChange={handleOptionsChange}
          onNext={() => setCurrentStep(3)}
          onBack={() => setCurrentStep(1)}
        />
      )}

      {currentStep === 3 && (
        <Step3Notes
          courseCode={academicData.courseCode}
          scheme={academicData.scheme}
          notesChoice={notesChoice}
          uploadedNotes={uploadedNotes}
          onChoiceChange={setNotesChoice}
          onNotesUploaded={setUploadedNotes}
          onNext={handleGeneratePlan}
          onBack={() => setCurrentStep(2)}
          isGeneratingPlan={isGeneratingPlan}
        />
      )}

      {currentStep === 4 && activePlan && (
        <Step4Timetable plan={activePlan} onReset={handleResetPlan} />
      )}
    </div>
  );
};
