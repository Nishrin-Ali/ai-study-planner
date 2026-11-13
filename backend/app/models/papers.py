import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def generate_paper_id() -> str:
    return str(uuid.uuid4())


def generate_question_id() -> str:
    return str(uuid.uuid4())


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(String, primary_key=True, default=generate_paper_id)
    course_code = Column(String, index=True, nullable=False)
    scheme = Column(String, nullable=False, default="2022")
    branch = Column(String, nullable=True)
    semester = Column(Integer, nullable=True)
    exam_session = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    status = Column(String, default="validated")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="paper", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=generate_question_id)
    paper_id = Column(String, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False)
    module = Column(Integer, nullable=False)
    question_number = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=True, default=10)
    page_number = Column(Integer, nullable=True, default=1)

    paper = relationship("QuestionPaper", back_populates="questions")
