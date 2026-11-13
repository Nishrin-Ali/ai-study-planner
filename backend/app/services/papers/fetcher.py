"""VTU Question Paper Fetcher and Ingestion Service.

Performs web search (via Tavily API or HTTP), downloads PDFs with rate-limiting,
validates VTU authenticity, extracts questions, and caches them to SQLite via SQLAlchemy.
Provides background task execution and job progress polling.
"""
import asyncio
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

import httpx

from app.database import SessionLocal
from app.models.papers import Question, QuestionPaper
from app.services.papers.extractor import extract_questions_from_pdf_data
from app.services.security import download_secure_pdf, SSRFSecurityError

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "papers_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SEEDS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "seed_papers.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VTUStudentAssistant/1.0"
MAX_PDF_SIZE = 25 * 1024 * 1024  # 25 MB
REQUEST_TIMEOUT = 12.0  # seconds

# Global in-memory dictionary for tracking job statuses
JOBS: Dict[str, Dict[str, Any]] = {}


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return JOBS.get(job_id)


def update_job(
    job_id: str,
    status: Optional[str] = None,
    progress_pct: Optional[int] = None,
    message: Optional[str] = None,
    papers_found: Optional[int] = None,
    papers_validated: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    if job_id not in JOBS:
        return
    job = JOBS[job_id]
    if status is not None:
        job["status"] = status
    if progress_pct is not None:
        job["progress_pct"] = progress_pct
    if message is not None:
        job["message"] = message
    if papers_found is not None:
        job["papers_found"] = papers_found
    if papers_validated is not None:
        job["papers_validated"] = papers_validated
    if error:
        job["errors"].append(error)


async def search_tavily(query: str, api_key: str) -> List[str]:
    """Search Tavily for question paper PDF links."""
    pdf_urls: List[str] = []
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 7,
        "include_domains": [
            "vtu.ac.in",
            "vturesource.com",
            "takeitsmart.in",
            "azdocuments.in",
            "vtupulse.com"
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post("https://api.tavily.com/search", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("results", []):
                    url = result.get("url", "")
                    if url and (url.endswith(".pdf") or "drive.google" in url or "download" in url or "qp" in url):
                        pdf_urls.append(url)
                    elif url:
                        pdf_urls.append(url)
            else:
                logger.warning(f"Tavily search returned status {resp.status_code}: {resp.text}")
    except Exception as exc:
        logger.warning(f"Error during Tavily search: {exc}")

    return pdf_urls


async def download_file(url: str) -> Optional[bytes]:
    """Download a PDF file safely via secure HTTP client with SSRF protection, timeout, and max size cap."""
    try:
        return await download_secure_pdf(url)
    except SSRFSecurityError as ssrf_err:
        logger.warning(f"Blocked SSRF attempt when fetching {url}: {ssrf_err}")
    except ValueError as val_err:
        logger.warning(f"Validation failure when downloading {url}: {val_err}")
    except Exception as exc:
        logger.warning(f"Download error for {url}: {exc}")
    return None


def load_seed_papers_into_db(db, course_code: str, scheme: str) -> int:
    """Populate database from seeds if web papers are insufficient."""
    norm_code = course_code.strip().upper()
    if not SEEDS_FILE.exists():
        return 0

    seeded_count = 0
    try:
        with open(SEEDS_FILE, "r", encoding="utf-8") as f:
            seeds = json.load(f)

        for paper_data in seeds:
            if paper_data.get("course_code", "").strip().upper() != norm_code:
                continue

            paper_id = paper_data.get("id")
            existing = db.query(QuestionPaper).filter(QuestionPaper.id == paper_id).first()
            if existing:
                continue

            paper = QuestionPaper(
                id=paper_id,
                course_code=norm_code,
                scheme=paper_data.get("scheme", scheme or "2022"),
                branch=paper_data.get("branch", "CSE"),
                semester=paper_data.get("semester", 3),
                exam_session=paper_data.get("exam_session", "Unknown Session"),
                source_url=paper_data.get("source_url"),
                file_path=paper_data.get("file_path"),
                status=paper_data.get("status", "validated"),
                fetched_at=datetime.utcnow()
            )
            db.add(paper)
            db.flush()

            for idx, q_data in enumerate(paper_data.get("questions", []), 1):
                q = Question(
                    id=str(uuid.uuid4()),
                    paper_id=paper.id,
                    module=int(q_data.get("module", 1)),
                    question_number=str(q_data.get("question_number", f"{idx}.a")),
                    text=str(q_data.get("text", "")).strip(),
                    marks=int(q_data.get("marks", 10)),
                )
                db.add(q)
            seeded_count += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(f"Failed loading seed papers into db: {exc}")

    return seeded_count


async def run_paper_fetch_job(
    job_id: str,
    course_code: str,
    course_title: Optional[str],
    scheme: str
) -> None:
    """Asynchronous background worker to discover, download, validate, and cache papers."""
    norm_code = course_code.strip().upper()
    title_str = f" {course_title}" if course_title else ""
    tavily_key = os.getenv("TAVILY_API_KEY")

    update_job(job_id, progress_pct=10, message=f"Formulating queries for {norm_code} ({scheme} scheme)...")

    db = SessionLocal()
    try:
        # Check existing validated papers
        existing_count = (
            db.query(QuestionPaper)
            .filter(QuestionPaper.course_code == norm_code)
            .filter(QuestionPaper.status == "validated")
            .count()
        )

        discovered_urls: List[str] = []

        # Web search if Tavily configured
        if tavily_key:
            update_job(job_id, progress_pct=25, message=f"Searching web repositories for {norm_code} question papers...")
            queries = [
                f"{norm_code} VTU question paper",
                f"{norm_code}{title_str} VTU previous question paper",
                f"{norm_code} {scheme} scheme VTU question paper filetype:pdf"
            ]
            for q in queries:
                await asyncio.sleep(1.2)  # Rate limit 1-2s delay
                urls = await search_tavily(q, tavily_key)
                discovered_urls.extend(urls)

            discovered_urls = list(dict.fromkeys(discovered_urls))
            update_job(job_id, papers_found=len(discovered_urls))

        newly_validated = 0
        if discovered_urls:
            update_job(job_id, progress_pct=45, message=f"Found {len(discovered_urls)} candidate links. Downloading and validating...")

            for url in discovered_urls[:5]:
                await asyncio.sleep(1.5)  # Rate limit between downloads
                pdf_bytes = await download_file(url)
                if not pdf_bytes:
                    continue

                is_valid, reason, session, questions, raw_text = await extract_questions_from_pdf_data(
                    pdf_bytes, course_code=norm_code, scheme=scheme
                )

                if is_valid and session:
                    paper_id = f"qp_{hashlib.md5(url.encode()).hexdigest()[:8]}"
                    # Check if already saved
                    if not db.query(QuestionPaper).filter(QuestionPaper.id == paper_id).first():
                        save_path = CACHE_DIR / f"{paper_id}.pdf"
                        try:
                            with open(save_path, "wb") as f:
                                f.write(pdf_bytes)
                        except Exception:
                            save_path = None

                        paper = QuestionPaper(
                            id=paper_id,
                            course_code=norm_code,
                            scheme=scheme,
                            exam_session=session,
                            source_url=url,
                            file_path=str(save_path) if save_path else None,
                            status="validated",
                            fetched_at=datetime.utcnow()
                        )
                        db.add(paper)
                        db.flush()

                        for idx, q_data in enumerate(questions, 1):
                            q = Question(
                                id=str(uuid.uuid4()),
                                paper_id=paper.id,
                                module=int(q_data.get("module", 1)),
                                question_number=str(q_data.get("question_number", f"{idx}.a")),
                                text=str(q_data.get("text", "")).strip(),
                                marks=int(q_data.get("marks", 10)),
                            )
                            db.add(q)

                        db.commit()
                        newly_validated += 1
                        update_job(job_id, papers_validated=existing_count + newly_validated)

        # Graceful fallback: If total papers < 2, load verified seeds!
        total_valid = existing_count + newly_validated
        seed_notice = ""

        if total_valid < 2:
            update_job(job_id, progress_pct=75, message="Web search returned < 2 valid papers. Loading authentic seed papers...")
            seeded = load_seed_papers_into_db(db, norm_code, scheme)
            if seeded > 0:
                total_valid += seeded
                seed_notice = f" Loaded {seeded} pre-verified VTU exam sessions from verified seed archive."
            else:
                seed_notice = " No offline seed papers found for this course code."

        final_count = (
            db.query(QuestionPaper)
            .filter(QuestionPaper.course_code == norm_code)
            .filter(QuestionPaper.status == "validated")
            .count()
        )

        msg = f"Completed: {final_count} verified question papers available for {norm_code}.{seed_notice}"
        update_job(
            job_id,
            status="completed",
            progress_pct=100,
            message=msg,
            papers_found=max(len(discovered_urls), final_count),
            papers_validated=final_count
        )
    except Exception as exc:
        logger.exception(f"Paper fetch job {job_id} encountered error: {exc}")
        update_job(job_id, status="failed", progress_pct=100, message=f"Job failed: {exc}", error=str(exc))
    finally:
        db.close()


def start_fetch_job(course_code: str, course_title: Optional[str], scheme: str) -> str:
    """Initialize a background fetch job and start the worker task."""
    job_id = f"job_{uuid.uuid4().hex}"
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "in_progress",
        "progress_pct": 0,
        "message": f"Started fetching question papers for {course_code} ({scheme}).",
        "papers_found": 0,
        "papers_validated": 0,
        "errors": []
    }

    loop = asyncio.get_event_loop()
    loop.create_task(run_paper_fetch_job(job_id, course_code, course_title, scheme))

    return job_id
