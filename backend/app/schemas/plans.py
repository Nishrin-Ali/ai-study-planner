from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class PlanCreateRequest(BaseModel):
    course_code: str
    course_title: str
    branch: str
    semester: int
    scheme: str
    num_modules: int = Field(..., ge=1, le=5)
    num_days: int = Field(..., ge=1, le=30)
    only_important_questions: bool = True
    notes_id: Optional[str] = None


class PlanItemResponse(BaseModel):
    id: str
    type: str  # "study" | "break"
    module: Optional[int] = None
    title: str
    start_time: str
    end_time: str
    duration_minutes: int
    answer_id: Optional[str] = None
    is_completed: bool = False


class PlanDayResponse(BaseModel):
    day_number: int
    date_label: str
    total_study_minutes: int
    items: List[PlanItemResponse]


class AnswerResponse(BaseModel):
    id: str
    question_or_topic: str
    module: Optional[int] = None
    content: str
    source_type: str  # "notes" | "web" | "curriculum_grounded"
    source_attribution: str
    source_urls: List[str] = []


class StudyPlanResponse(BaseModel):
    plan_id: str
    course_code: str
    course_title: str
    num_days: int
    num_modules: int
    is_heavy_plan: bool
    heavy_warning: Optional[str] = None
    created_at: datetime
    days: List[PlanDayResponse]
    answers: Dict[str, AnswerResponse]


class PlanItemToggleRequest(BaseModel):
    is_completed: bool


class PlanItemToggleResponse(BaseModel):
    item_id: str
    is_completed: bool


class TopicEffortItem(BaseModel):
    topic: str
    module: int
    recommended_minutes: int = Field(..., ge=10, le=90)
    reasoning: Optional[str] = None


class TopicEffortEstimationOutput(BaseModel):
    topics: List[TopicEffortItem]


class SingleAnswerOutput(BaseModel):
    answer: str
    attribution: str
    source_urls: List[str] = []
