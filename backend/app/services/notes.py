import re
import io
import logging
from typing import List, Tuple, Set
import pymupdf as fitz  # PyMuPDF
from app.config import settings
from app.services.gemini import transcribe_multimodal, GeminiNotConfiguredError

logger = logging.getLogger(__name__)

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5
}


def detect_modules_from_text(text: str) -> List[int]:
    """
    Search extracted text for module / unit indicators (e.g. 'Module 1', 'Unit 2', 'MODULE - IV').
    Returns sorted list of unique module integers (1 to 5).
    """
    detected: Set[int] = set()

    # Pattern for "Module 1", "Unit 2", "Module - 3", etc.
    digits_pattern = re.compile(r'(?:module|unit)\s*[-:]?\s*([1-5])\b', re.IGNORECASE)
    for match in digits_pattern.finditer(text):
        try:
            mod_num = int(match.group(1))
            if 1 <= mod_num <= 5:
                detected.add(mod_num)
        except ValueError:
            pass

    # Pattern for roman numerals "Module I", "Unit IV", etc.
    roman_pattern = re.compile(r'(?:module|unit)\s*[-:]?\s*([IVXivx]{1,3})\b', re.IGNORECASE)
    for match in roman_pattern.finditer(text):
        roman = match.group(1).upper()
        if roman in ROMAN_TO_INT:
            detected.add(ROMAN_TO_INT[roman])

    # If no explicit "Module X" found, fallback to check for standard section headers
    if not detected:
        # Check if text contains references like M1, M2
        short_pattern = re.compile(r'\bM([1-5])\b')
        for match in short_pattern.finditer(text):
            detected.add(int(match.group(1)))

    # If still none detected, default to [1, 2, 3, 4, 5] if comprehensive or [1, 2, 3]
    return sorted(list(detected)) if detected else [1, 2, 3]


async def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, int, List[int]]:
    """
    Extracts text and detects modules from a PDF.
    If extracted text < 50 chars (e.g. scanned handwritten or image PDF),
    falls back to Gemini Multimodal transcription.

    Returns:
        (extracted_text, pages_count, detected_modules)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_count = len(doc)
    page_texts: List[str] = []

    for page_num in range(pages_count):
        page = doc.load_page(page_num)
        text = page.get_text()
        if text:
            page_texts.append(text)

    combined_text = "\n".join(page_texts).strip()

    # Fallback to Gemini Multimodal if text is sparse (< 50 chars)
    if len(combined_text) < 50:
        logger.info("PyMuPDF extracted only %d chars (<50). Attempting Gemini Multimodal fallback...", len(combined_text))
        if settings.has_gemini:
            try:
                ai_text = await transcribe_multimodal(
                    pdf_bytes,
                    mime_type="application/pdf",
                    prompt="Transcribe all study notes and technical content from these pages accurately. Identify all VTU modules and topics."
                )
                if ai_text and len(ai_text.strip()) > len(combined_text):
                    combined_text = ai_text.strip()
            except GeminiNotConfiguredError:
                logger.warning("Gemini API key missing; skipping multimodal fallback.")
            except Exception as e:
                logger.error("Multimodal transcription failed: %s", e)
        else:
            logger.info("GEMINI_API_KEY is not configured; cannot transcribe scanned PDF.")

    detected_modules = detect_modules_from_text(combined_text)

    return combined_text, pages_count, detected_modules
