import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from app.database import Base


def generate_notes_id() -> str:
    return str(uuid.uuid4())


class UploadedNotes(Base):
    __tablename__ = "uploaded_notes"

    id = Column(String, primary_key=True, default=generate_notes_id)
    course_code = Column(String, index=True, nullable=False)
    scheme = Column(String, nullable=False, default="2022")
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True, default=0)
    pages_count = Column(Integer, nullable=True, default=0)
    detected_modules = Column(JSON, default=list)  # List[int]
    text_excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
