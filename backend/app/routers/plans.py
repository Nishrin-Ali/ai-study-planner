from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.plans import StudyPlan, PlanItem, Answer, generate_plan_id
from app.models.notes import UploadedNotes
from app.schemas.plans import (
    PlanCreateRequest,
    StudyPlanResponse,
    PlanDayResponse,
    PlanItemResponse,
    AnswerResponse,
    PlanItemToggleRequest,
    PlanItemToggleResponse,
)
from app.services.planner import generate_plan_schedule

router = APIRouter(prefix="/api/plan", tags=["Study Plans"])


@router.post("", response_model=StudyPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_study_plan(request: PlanCreateRequest, db: Session = Depends(get_db)):
    """
    Generate a deterministic timetable with AI topic effort estimation and answers.
    Takes syllabus parameters, calculates days, interleaves study sessions and breaks,
    and returns full timetable with grounded answers.
    """
    notes_record = None
    if request.notes_id:
        notes_record = db.query(UploadedNotes).filter(UploadedNotes.id == request.notes_id).first()

    plan_id = generate_plan_id()

    # Generate timetable data
    is_heavy, heavy_warning, days_data, answers_data = generate_plan_schedule(
        course_code=request.course_code,
        course_title=request.course_title,
        num_days=request.num_days,
        num_modules=request.num_modules,
        notes_record=notes_record,
    )

    created_at = datetime.utcnow()

    # Save StudyPlan record
    db_plan = StudyPlan(
        id=plan_id,
        course_code=request.course_code,
        course_title=request.course_title,
        num_days=request.num_days,
        num_modules=request.num_modules,
        is_heavy_plan=is_heavy,
        heavy_warning=heavy_warning,
        created_at=created_at,
    )
    db.add(db_plan)

    # Save Answers
    answers_map: Dict[str, AnswerResponse] = {}
    for a in answers_data:
        db_answer = Answer(
            id=a["id"],
            plan_id=plan_id,
            question_or_topic=a["question_or_topic"],
            module=a["module"],
            content=a["content"],
            source_type=a["source_type"],
            source_attribution=a["source_attribution"],
            source_urls=a["source_urls"],
        )
        db.add(db_answer)
        answers_map[a["id"]] = AnswerResponse(
            id=a["id"],
            question_or_topic=a["question_or_topic"],
            module=a["module"],
            content=a["content"],
            source_type=a["source_type"],
            source_attribution=a["source_attribution"],
            source_urls=a["source_urls"],
        )

    # Save PlanItems
    response_days = []
    for day in days_data:
        day_items_resp = []
        for item in day["items"]:
            db_item = PlanItem(
                id=item["id"],
                plan_id=plan_id,
                day_number=day["day_number"],
                type=item["type"],
                module=item["module"],
                title=item["title"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                duration_minutes=item["duration_minutes"],
                is_completed=item["is_completed"],
                answer_id=item["answer_id"],
            )
            db.add(db_item)
            day_items_resp.append(PlanItemResponse(**item))

        response_days.append(
            PlanDayResponse(
                day_number=day["day_number"],
                date_label=day["date_label"],
                total_study_minutes=day["total_study_minutes"],
                items=day_items_resp,
            )
        )

    db.commit()

    return StudyPlanResponse(
        plan_id=plan_id,
        course_code=request.course_code,
        course_title=request.course_title,
        num_days=request.num_days,
        num_modules=request.num_modules,
        is_heavy_plan=is_heavy,
        heavy_warning=heavy_warning,
        created_at=created_at,
        days=response_days,
        answers=answers_map,
    )


@router.get("/{plan_id}", response_model=StudyPlanResponse)
async def get_study_plan(plan_id: str, db: Session = Depends(get_db)):
    """
    Fetch an existing study plan by ID with all day items and answer definitions.
    """
    db_plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan '{plan_id}' not found."
        )

    # Build answers dictionary
    answers_map: Dict[str, AnswerResponse] = {}
    for ans in db_plan.answers:
        answers_map[ans.id] = AnswerResponse(
            id=ans.id,
            question_or_topic=ans.question_or_topic,
            module=ans.module,
            content=ans.content,
            source_type=ans.source_type,
            source_attribution=ans.source_attribution,
            source_urls=ans.source_urls or [],
        )

    # Group items by day
    days_dict: Dict[int, list] = {}
    for item in db_plan.items:
        if item.day_number not in days_dict:
            days_dict[item.day_number] = []
        days_dict[item.day_number].append(
            PlanItemResponse(
                id=item.id,
                type=item.type,
                module=item.module,
                title=item.title,
                start_time=item.start_time,
                end_time=item.end_time,
                duration_minutes=item.duration_minutes,
                answer_id=item.answer_id,
                is_completed=item.is_completed,
            )
        )

    response_days = []
    for day_num in sorted(days_dict.keys()):
        items = days_dict[day_num]
        study_mins = sum(it.duration_minutes for it in items if it.type == "study")
        date_label = "Day 1 (Today)" if day_num == 1 else f"Day {day_num}"
        response_days.append(
            PlanDayResponse(
                day_number=day_num,
                date_label=date_label,
                total_study_minutes=study_mins,
                items=items,
            )
        )

    return StudyPlanResponse(
        plan_id=db_plan.id,
        course_code=db_plan.course_code,
        course_title=db_plan.course_title,
        num_days=db_plan.num_days,
        num_modules=db_plan.num_modules,
        is_heavy_plan=db_plan.is_heavy_plan,
        heavy_warning=db_plan.heavy_warning,
        created_at=db_plan.created_at,
        days=response_days,
        answers=answers_map,
    )


@router.patch("/{plan_id}/items/{item_id}", response_model=PlanItemToggleResponse)
async def toggle_plan_item(
    plan_id: str,
    item_id: str,
    payload: PlanItemToggleRequest,
    db: Session = Depends(get_db)
):
    """
    Toggle or update the completion status of a specific plan item.
    """
    item = db.query(PlanItem).filter(PlanItem.id == item_id, PlanItem.plan_id == plan_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan item '{item_id}' for plan '{plan_id}' not found."
        )

    item.is_completed = payload.is_completed
    db.commit()
    db.refresh(item)

    return PlanItemToggleResponse(item_id=item.id, is_completed=item.is_completed)
