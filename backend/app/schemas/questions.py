from typing import List, Optional
from pydantic import BaseModel, Field


class StructuredExtractedQuestion(BaseModel):
    module: int = Field(..., description="Module number (1 to 5)")
    question_number: str = Field(..., description="e.g. 1a, 1b, 2a, etc.")
    text: str = Field(..., description="Full text of the question")
    marks: Optional[int] = Field(10, description="Marks assigned, default 10 if unspecified")


class PaperExtractionOutput(BaseModel):
    exam_session: Optional[str] = Field(None, description="Extracted exam session e.g. Feb/Mar 2023")
    course_code: Optional[str] = Field(None, description="Course code e.g. BCS304")
    questions: List[StructuredExtractedQuestion] = Field(default_factory=list)


class ImportantQuestionsRequest(BaseModel):
    course_code: str
    scheme: str
    selected_modules: List[int]


class RepetitionQuestionItem(BaseModel):
    id: str
    canonical_question: str
    module: int
    repetition_count: int
    repetition_label: str
    sessions: List[str]
    marks: Optional[int] = 10


class RepetitionModuleGroup(BaseModel):
    module: int
    questions: List[RepetitionQuestionItem]


class ImportantQuestionsResponse(BaseModel):
    course_code: str
    scheme: str
    total_papers_analyzed: int
    exam_sessions: List[str]
    is_reliable: bool
    message: str
    modules: List[RepetitionModuleGroup]


class ClusteredQuestionOutput(BaseModel):
    canonical_question: str
    module: int
    repetition_count: int
    sessions: List[str]
    marks: Optional[int] = 10


class RepetitionClusteringOutput(BaseModel):
    clusters: List[ClusteredQuestionOutput]
