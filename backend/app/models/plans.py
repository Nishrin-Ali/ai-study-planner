import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_plan_id() -> str:
    return str(uuid.uuid4())


def generate_item_id() -> str:
    return str(uuid.uuid4())


def generate_answer_id() -> str:
    return str(uuid.uuid4())


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(String, primary_key=True, default=generate_plan_id)
    course_code = Column(String, index=True, nullable=False)
    course_title = Column(String, nullable=False)
    num_days = Column(Integer, nullable=False)
    num_modules = Column(Integer, nullable=False)
    is_heavy_plan = Column(Boolean, default=False)
    heavy_warning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.day_number, PlanItem.start_time")
    answers = relationship("Answer", back_populates="plan", cascade="all, delete-orphan")


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(String, primary_key=True, default=generate_item_id)
    plan_id = Column(String, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    day_number = Column(Integer, nullable=False)
    type = Column(String, nullable=False)  # "study" | "break"
    module = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    start_time = Column(String, nullable=False)  # "09:00"
    end_time = Column(String, nullable=False)    # "10:15"
    duration_minutes = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=False)
    answer_id = Column(String, ForeignKey("answers.id", ondelete="SET NULL"), nullable=True)

    plan = relationship("StudyPlan", back_populates="items")
    answer = relationship("Answer", back_populates="items")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=generate_answer_id)
    plan_id = Column(String, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    question_or_topic = Column(String, nullable=False)
    module = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    source_type = Column(String, nullable=False, default="curriculum_grounded")  # "notes" | "web" | "curriculum_grounded"
    source_attribution = Column(String, nullable=False)
    source_urls = Column(JSON, default=list)  # List[str]

    plan = relationship("StudyPlan", back_populates="answers")
    items = relationship("PlanItem", back_populates="answer")
