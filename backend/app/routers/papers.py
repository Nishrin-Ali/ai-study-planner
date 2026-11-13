"""FastAPI Router for Question Papers and Important Questions Subsystem."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.papers import Question, QuestionPaper
from app.schemas.papers import (
    ImportantQuestionsRequest,
    ImportantQuestionsResponse,
    PaperFetchRequest,
    PaperFetchResponse,
    PaperJobStatusResponse,
    PaperSummaryResponse,
)
from app.services.papers.extractor import extract_questions_from_pdf_data
from app.services.papers.fetcher import get_job_status, start_fetch_job
from app.services.papers.repetition import analyze_important_questions, ensure_seeds_loaded

router = APIRouter(prefix="/api", tags=["Papers"])

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "papers_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/papers/fetch",
    response_model=PaperFetchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous background web search and ingestion"
)
async def fetch_question_papers(request: PaperFetchRequest):
    """Trigger background web discovery and ingestion of VTU previous question papers."""
    job_id = start_fetch_job(
        course_code=request.course_code,
        course_title=request.course_title,
        scheme=request.scheme,
    )
    return PaperFetchResponse(
        job_id=job_id,
        status="in_progress",
        message="Started fetching question papers from public repositories."
    )


@router.get(
    "/papers/fetch/{job_id}",
    response_model=PaperJobStatusResponse,
    summary="Check progress of paper discovery and extraction"
)
async def get_fetch_job_status(job_id: str):
    """Poll the status and progress of a background question paper fetch job."""
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    return PaperJobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress_pct=job["progress_pct"],
        message=job["message"],
        papers_found=job.get("papers_found", 0),
        papers_validated=job.get("papers_validated", 0),
        errors=job.get("errors", [])
    )


@router.get(
    "/papers",
    response_model=List[PaperSummaryResponse],
    summary="Query cached papers from database"
)
async def get_cached_papers(
    course_code: Optional[str] = None,
    scheme: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List cached and validated previous exam question papers for course_code & scheme."""
    if course_code:
        # Pre-seed if DB is empty for this course
        ensure_seeds_loaded(db, course_code, scheme)

    query = db.query(QuestionPaper)
    if course_code:
        query = query.filter(QuestionPaper.course_code == course_code.strip().upper())
    if scheme:
        query = query.filter(QuestionPaper.scheme == scheme.strip())

    papers = query.order_by(QuestionPaper.fetched_at.desc()).all()

    summaries = []
    for p in papers:
        summaries.append(PaperSummaryResponse(
            id=p.id,
            course_code=p.course_code,
            scheme=p.scheme,
            exam_session=p.exam_session,
            source_url=p.source_url,
            status=p.status or "validated",
            questions_count=len(p.questions),
            fetched_at=p.fetched_at.isoformat() if p.fetched_at else ""
        ))
    return summaries


@router.post(
    "/papers/upload",
    summary="Manual upload of a question paper PDF for the library"
)
async def upload_question_paper(
    file: UploadFile = File(...),
    course_code: str = Form(...),
    scheme: str = Form(...),
    branch: Optional[str] = Form(None),
    semester: Optional[int] = Form(None),
    exam_session: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a VTU question paper PDF manually.

    Validates VTU headers, extracts questions module-wise, and caches to DB.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a PDF document."
        )

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed 25MB limit."
        )

    is_valid, reason, detected_session, questions, raw_text = await extract_questions_from_pdf_data(
        pdf_bytes=pdf_bytes,
        course_code=course_code,
        scheme=scheme
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"VTU Paper Validation Failed: {reason}"
        )

    final_session = exam_session or detected_session or "Exam Session"
    paper_id = f"qp_up_{uuid.uuid4().hex[:6]}"
    file_path = CACHE_DIR / f"{paper_id}_{file.filename}"

    try:
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
    except Exception:
        file_path = None

    paper = QuestionPaper(
        id=paper_id,
        course_code=course_code.strip().upper(),
        scheme=scheme.strip(),
        branch=branch,
        semester=semester,
        exam_session=final_session,
        source_url=f"uploaded://{file.filename}",
        file_path=str(file_path) if file_path else None,
        status="validated",
        fetched_at=datetime.utcnow()
    )
    db.add(paper)
    db.flush()

    for idx, q_data in enumerate(questions, 1):
        q = Question(
            id=f"q_{paper.id}_{idx}",
            paper_id=paper.id,
            module=int(q_data.get("module", 1)),
            question_number=str(q_data.get("question_number", f"{idx}.a")),
            text=str(q_data.get("text", "")).strip(),
            marks=int(q_data.get("marks", 10)),
        )
        db.add(q)

    db.commit()

    return {
        "id": paper_id,
        "filename": file.filename,
        "course_code": course_code.upper(),
        "scheme": scheme,
        "exam_session": final_session,
        "status": "validated",
        "questions_count": len(questions),
        "message": f"Successfully validated and parsed {len(questions)} questions from uploaded paper."
    }


@router.post(
    "/important-questions",
    response_model=ImportantQuestionsResponse,
    summary="Compute canonical question clusters and repetition counts across cached papers"
)
async def get_important_questions(
    request: ImportantQuestionsRequest,
    db: Session = Depends(get_db)
):
    """Compute canonical question clusters and repetition counts across cached papers."""
    return await analyze_important_questions(
        course_code=request.course_code,
        scheme=request.scheme,
        selected_modules=request.selected_modules,
        db=db
    )
