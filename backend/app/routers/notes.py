import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notes import UploadedNotes, generate_notes_id
from app.schemas.notes import NotesUploadResponse
from app.services.notes import extract_text_from_pdf

router = APIRouter(prefix="/api/notes", tags=["Notes"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "notes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=NotesUploadResponse)
async def upload_notes(
    file: UploadFile = File(...),
    course_code: str = Form(...),
    scheme: str = Form("2022"),
    db: Session = Depends(get_db),
):
    """
    Upload and parse lecture notes PDF (up to 20MB).
    Extracts text using PyMuPDF (with Gemini Multimodal fallback) and detects modules.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for notes upload."
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 20MB (received {file_size / (1024*1024):.1f}MB)."
        )

    # Save to disk
    notes_id = generate_notes_id()
    safe_filename = f"{notes_id}_{Path(file.filename).name}"
    save_path = UPLOAD_DIR / safe_filename
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Extract text and detected modules
    try:
        extracted_text, pages_count, detected_modules = await extract_text_from_pdf(file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF content: {exc}"
        )

    # Create database record
    text_excerpt = extracted_text[:1500] if extracted_text else ""
    notes_record = UploadedNotes(
        id=notes_id,
        course_code=course_code,
        scheme=scheme,
        filename=file.filename,
        file_path=str(save_path),
        file_size=file_size,
        pages_count=pages_count,
        detected_modules=detected_modules,
        text_excerpt=text_excerpt,
    )
    db.add(notes_record)
    db.commit()
    db.refresh(notes_record)

    return NotesUploadResponse(
        notes_id=notes_record.id,
        filename=notes_record.filename,
        file_size=file_size,
        pages_count=pages_count,
        detected_modules=detected_modules,
        message=f"Successfully parsed {pages_count} pages of notes."
    )
