from typing import List, Optional
from pydantic import BaseModel


class NotesUploadResponse(BaseModel):
    notes_id: str
    filename: str
    file_size: int
    pages_count: int
    detected_modules: List[int]
    message: str


class NotesSummary(BaseModel):
    id: str
    course_code: str
    scheme: str
    filename: str
    file_size: int
    pages_count: int
    detected_modules: List[int]
