export interface CatalogBranch {
  code: string;
  name: string;
  semesters: number[];
}

export interface CatalogCourse {
  code: string;
  title: string;
  branch: string;
  semester: number;
  scheme: string;
  credits?: number;
  verified?: boolean;
  source_url?: string;
}

export interface CatalogResponse {
  university: string;
  schemes: string[];
  branches: CatalogBranch[];
  courses: CatalogCourse[];
}

export interface NotesUploadResponse {
  notes_id: string;
  filename: string;
  file_size: number;
  pages_count: number;
  detected_modules: number[];
  message: string;
}

export interface QuestionPaperSummary {
  id: string;
  course_code: string;
  scheme: string;
  branch?: string;
  semester?: number;
  exam_session: string;
  source_url: string;
  status: string;
  questions_count?: number;
  fetched_at: string;
  has_file?: boolean;
  file_url?: string | null;
}

export interface FetchJobProgress {
  job_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_pct: number;
  message: string;
  papers_found: number;
  papers_validated: number;
  errors: string[];
}

export interface ImportantQuestion {
  id: string;
  canonical_question: string;
  module: number;
  repetition_count: number;
  repetition_label: string;
  sessions: string[];
  marks: number;
  paper_ids?: string[];
  primary_paper_id?: string | null;
  page_number?: number;
}

export interface ModuleQuestions {
  module: number;
  questions: ImportantQuestion[];
}

export interface ImportantQuestionsResponse {
  course_code: string;
  scheme: string;
  total_papers_analyzed: number;
  exam_sessions: string[];
  is_reliable: boolean;
  message: string;
  modules: ModuleQuestions[];
}

export interface TimetableItem {
  id: string;
  type: 'study' | 'break' | 'lunch' | 'revision';
  module: number | null;
  title: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  answer_id?: string | null;
  is_completed?: boolean;
}

export interface TimetableDay {
  day_number: number;
  date_label: string;
  total_study_minutes: number;
  items: TimetableItem[];
}

export interface PlanAnswer {
  id: string;
  question_or_topic: string;
  module: number;
  content: string;
  source_type: 'notes' | 'web' | 'curriculum_grounded';
  source_attribution: string;
  source_urls?: string[];
}

export interface StudyPlanResponse {
  plan_id: string;
  course_code: string;
  course_title: string;
  num_days: number;
  num_modules: number;
  is_heavy_plan: boolean;
  heavy_warning: string | null;
  created_at: string;
  days: TimetableDay[];
  answers: Record<string, PlanAnswer>;
}
