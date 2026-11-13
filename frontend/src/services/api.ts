import {
  CatalogResponse,
  NotesUploadResponse,
  QuestionPaperSummary,
  FetchJobProgress,
  ImportantQuestionsResponse,
  StudyPlanResponse,
} from '../types/api';

const API_BASE = '/api';

export async function getCatalog(): Promise<CatalogResponse> {
  const res = await fetch(`${API_BASE}/catalog`);
  if (!res.ok) throw new Error('Failed to load VTU catalog');
  return res.json();
}

export async function uploadNotes(file: File, courseCode: string, scheme: string): Promise<NotesUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('course_code', courseCode);
  formData.append('scheme', scheme);

  const res = await fetch(`${API_BASE}/notes/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Failed to upload notes');
  }
  return res.json();
}

export async function startPaperFetch(courseCode: string, courseTitle: string, scheme: string): Promise<{ job_id: string; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/papers/fetch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course_code: courseCode,
      course_title: courseTitle,
      scheme,
    }),
  });
  if (!res.ok) throw new Error('Failed to start paper fetcher');
  return res.json();
}

export async function getPaperFetchProgress(jobId: string): Promise<FetchJobProgress> {
  const res = await fetch(`${API_BASE}/papers/fetch/${jobId}`);
  if (!res.ok) throw new Error('Failed to check paper fetch progress');
  return res.json();
}

export async function getPapers(courseCode?: string, scheme?: string): Promise<QuestionPaperSummary[]> {
  const params = new URLSearchParams();
  if (courseCode) params.append('course_code', courseCode);
  if (scheme) params.append('scheme', scheme);

  const res = await fetch(`${API_BASE}/papers?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to load papers');
  return res.json();
}

export async function uploadPaper(
  file: File,
  courseCode: string,
  scheme: string,
  branch: string,
  semester: number,
  examSession: string
): Promise<{ id: string; message: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('course_code', courseCode);
  formData.append('scheme', scheme);
  formData.append('branch', branch);
  formData.append('semester', semester.toString());
  formData.append('exam_session', examSession);

  const res = await fetch(`${API_BASE}/papers/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Paper upload failed' }));
    throw new Error(err.detail || 'Paper upload failed');
  }
  return res.json();
}

export async function getImportantQuestions(courseCode: string, scheme: string, modules: number[]): Promise<ImportantQuestionsResponse> {
  const res = await fetch(`${API_BASE}/important-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course_code: courseCode,
      scheme,
      selected_modules: modules,
    }),
  });
  if (!res.ok) throw new Error('Failed to get important questions');
  return res.json();
}

export interface CreatePlanPayload {
  course_code: string;
  course_title: string;
  branch: string;
  semester: number;
  scheme: string;
  num_modules: number;
  num_days: number;
  only_important_questions: boolean;
  notes_id?: string | null;
}

export async function createStudyPlan(payload: CreatePlanPayload): Promise<StudyPlanResponse> {
  const res = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Plan generation failed' }));
    throw new Error(err.detail || 'Failed to generate study plan');
  }
  return res.json();
}

export async function getStudyPlan(planId: string): Promise<StudyPlanResponse> {
  const res = await fetch(`${API_BASE}/plan/${planId}`);
  if (!res.ok) throw new Error('Failed to load study plan');
  return res.json();
}

export async function togglePlanItemCompletion(planId: string, itemId: string, isCompleted: boolean): Promise<{ item_id: string; is_completed: boolean }> {
  const res = await fetch(`${API_BASE}/plan/${planId}/items/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_completed: isCompleted }),
  });
  if (!res.ok) throw new Error('Failed to update item completion');
  return res.json();
}
