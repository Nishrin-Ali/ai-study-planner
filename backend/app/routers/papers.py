"""FastAPI Router for Question Papers and Important Questions Subsystem."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.limiter import limiter
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
from app.services.security import is_safe_file_path

router = APIRouter(prefix="/api", tags=["Papers"])

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "papers_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seeds"


@router.post(
    "/papers/fetch",
    response_model=PaperFetchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous background web search and ingestion"
)
@limiter.limit("10/minute")
async def fetch_question_papers(request: Request, body: PaperFetchRequest):
    """Trigger background web discovery and ingestion of VTU previous question papers."""
    job_id = start_fetch_job(
        course_code=body.course_code,
        course_title=body.course_title,
        scheme=body.scheme,
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
        has_file = bool(p.file_path and Path(p.file_path).exists())
        summaries.append(PaperSummaryResponse(
            id=p.id,
            course_code=p.course_code,
            scheme=p.scheme,
            exam_session=p.exam_session,
            source_url=p.source_url,
            status=p.status or "validated",
            questions_count=len(p.questions),
            fetched_at=p.fetched_at.isoformat() if p.fetched_at else "",
            has_file=has_file,
            file_url=f"/api/papers/{p.id}/file" if has_file else None,
        ))
    return summaries


@router.get(
    "/papers/{paper_id}/file",
    summary="Stream validated question paper PDF inline with path-traversal safeguards"
)
async def get_paper_file(paper_id: str, db: Session = Depends(get_db)):
    """Stream cached question paper PDF inline with strict directory traversal prevention."""
    paper = db.query(QuestionPaper).filter(QuestionPaper.id == paper_id).first()
    if not paper or not paper.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question paper '{paper_id}' not found or has no attached PDF file."
        )

    file_path = Path(paper.file_path).resolve()
    # Check directory traversal
    if not is_safe_file_path(file_path, [CACHE_DIR, SEEDS_DIR]) or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested question paper PDF is unavailable on disk."
        )

    sanitized_session = (paper.exam_session or "exam").replace("/", "_").replace(" ", "_")
    download_filename = f"{paper.course_code}_{sanitized_session}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=download_filename,
        content_disposition_type="inline"
    )


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
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db)
):
    """Upload a VTU question paper PDF manually.

    Validates VTU headers, extracts questions module-wise, and caches to DB.
    """
    if settings.ADMIN_TOKEN and x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header for paper uploads."
        )

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

    # Magic byte verification: Must start with %PDF
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file: Missing %PDF file signature."
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
