"""Pydantic schemas for Question Papers and Repetition Analysis."""
from typing import List, Optional
from pydantic import BaseModel, Field


class PaperFetchRequest(BaseModel):
    course_code: str = Field(..., examples=["BCS304"])
    course_title: Optional[str] = Field(None, examples=["Data Structures and Applications"])
    scheme: str = Field(..., examples=["2022"])


class PaperFetchResponse(BaseModel):
    job_id: str
    status: str = "in_progress"
    message: str


class PaperJobStatusResponse(BaseModel):
    job_id: str
    status: str  # "in_progress" | "completed" | "failed"
    progress_pct: int
    message: str
    papers_found: int = 0
    papers_validated: int = 0
    errors: List[str] = []


class QuestionItem(BaseModel):
    module: int
    question_number: str
    text: str
    marks: int = 10
    sub_parts: List[str] = []


class PaperSummaryResponse(BaseModel):
    id: str
    course_code: str
    scheme: str
    exam_session: str
    source_url: Optional[str] = None
    status: str = "validated"
    questions_count: int = 0
    fetched_at: str


class ImportantQuestionsRequest(BaseModel):
    course_code: str = Field(..., examples=["BCS304"])
    scheme: str = Field(..., examples=["2022"])
    selected_modules: Optional[List[int]] = Field(None, examples=[[1, 2, 3]])


class CanonicalQuestionItem(BaseModel):
    id: str
    canonical_question: str
    module: int
    repetition_count: int
    repetition_label: str
    sessions: List[str]
    marks: int = 10


class ModuleQuestionsGroup(BaseModel):
    module: int
    questions: List[CanonicalQuestionItem]


class ImportantQuestionsResponse(BaseModel):
    course_code: str
    scheme: str
    total_papers_analyzed: int
    exam_sessions: List[str]
    is_reliable: bool
    message: str
    modules: List[ModuleQuestionsGroup]
