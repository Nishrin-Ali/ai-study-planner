"""VTU Question Paper PDF text and question extraction service.

Uses PyMuPDF (fitz) and Gemini structured output with heuristic fallbacks.
"""
import io
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Attempt to load genai SDK if available
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Attempt to load fitz (PyMuPDF)
try:
    import fitz
except ImportError:
    fitz = None

# Fallback pypdf
try:
    import pypdf
except ImportError:
    pypdf = None


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai:
        return genai.Client(api_key=api_key)
    return None


def extract_raw_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using fitz or pypdf."""
    text_chunks: List[str] = []

    if fitz:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text_chunks.append(page.get_text() or "")
            doc.close()
            combined = "\n".join(text_chunks).strip()
            if len(combined) >= 50:
                return combined
        except Exception as e:
            logger.warning(f"fitz extraction failed: {e}")

    if pypdf:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text_chunks.append(page.extract_text() or "")
            combined = "\n".join(text_chunks).strip()
            if len(combined) >= 50:
                return combined
        except Exception as e:
            logger.warning(f"pypdf extraction failed: {e}")

    # Fallback byte decoding search if libraries not present or text is raw
    try:
        raw_str = pdf_bytes.decode("latin1", errors="ignore")
        # Extract printable ascii words
        words = re.findall(r"[A-Za-z0-9,.:;()/\-\s]{5,}", raw_str)
        return " ".join(words)
    except Exception:
        return ""


def validate_vtu_paper(text: str, course_code: str, scheme: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """Strictly validate whether a PDF matches VTU standards, course code, and extract exam session.

    Returns: (is_valid, reason, detected_session)
    """
    clean_text = text.upper()
    norm_code = course_code.upper().replace(" ", "").replace("-", "")
    norm_text = clean_text.replace(" ", "").replace("-", "")

    # 1. Course Code Match
    if norm_code not in norm_text:
        return False, f"Course code '{course_code}' not found in document text.", None

    # 2. VTU Authenticity Headers
    vtu_markers = [
        "VISVESVARAYA TECHNOLOGICAL UNIVERSITY",
        "VTU",
        "BELAGAVI",
        "BELGAUM",
        "USN",
        "DEGREE EXAMINATION",
        "MAX. MARKS",
        "MAX MARKS: 100",
        "MAX MARKS: 50"
    ]
    matched_markers = [m for m in vtu_markers if m in clean_text]
    if len(matched_markers) < 2:
        return False, "Document lacks authentic VTU headers (e.g. USN, VTU Belagavi, Degree Examination).", None

    # 3. Exam Session Identification
    session_patterns = [
        r"(JAN(?:UARY)?\s*/\s*FEB(?:RUARY)?\s*20\d\d)",
        r"(JUNE?\s*/\s*JULY?\s*20\d\d)",
        r"(DEC(?:EMBER)?\s*20\d\d\s*/\s*JAN(?:UARY)?\s*20\d\d)",
        r"(FEB(?:RUARY)?\s*/\s*MAR(?:CH)?\s*20\d\d)",
        r"(JULY?\s*/\s*AUG(?:UST)?\s*20\d\d)",
        r"(DEC(?:EMBER)?\s*/\s*JAN(?:UARY)?\s*20\d\d)",
        r"(20\d\d\s*SCHEME)",
    ]

    detected_session = None
    for pattern in session_patterns:
        match = re.search(pattern, clean_text)
        if match:
            raw_match = match.group(1).title()
            # Normalize e.g. "Jan / Feb 2023" to "Jan/Feb 2023"
            detected_session = re.sub(r"\s*/\s*", "/", raw_match)
            break

    if not detected_session:
        # Fallback year search
        year_match = re.search(r"20(1[8-9]|2[0-9])", clean_text)
        if year_match:
            detected_session = f"Exam {year_match.group(0)}"
        else:
            detected_session = "Unknown Session"

    return True, "Validated successfully as authentic VTU exam paper.", detected_session


def extract_questions_rule_based(text: str) -> List[Dict[str, Any]]:
    """Heuristic rule-based module-wise question parser for VTU papers."""
    questions: List[Dict[str, Any]] = []

    # Try splitting text into Modules
    module_splits = re.split(r"(?:MODULE|UNIT)\s*[-:]?\s*([1-5])", text, flags=re.IGNORECASE)

    current_module = 1
    if len(module_splits) > 1:
        # module_splits format: [preamble, mod_num_1, mod_text_1, mod_num_2, mod_text_2, ...]
        i = 1
        while i < len(module_splits) - 1:
            try:
                mod_num = int(module_splits[i].strip())
            except ValueError:
                mod_num = current_module
            mod_text = module_splits[i + 1]

            mod_questions = _parse_module_questions(mod_text, mod_num)
            questions.extend(mod_questions)
            i += 2
    else:
        # If explicit MODULE header wasn't split, look for Q1 to Q10
        questions = _parse_numbered_questions(text)

    # If still empty, provide fallback questions partitioned across modules
    if not questions:
        questions = _fallback_heuristic_questions(text)

    return questions


def _parse_module_questions(mod_text: str, module_num: int) -> List[Dict[str, Any]]:
    questions = []
    # Match patterns like "1 a.", "1. a)", "Q1", "1 (a)"
    q_matches = list(re.finditer(
        r"(?:Q(?:UESTION)?\.?\s*)?(\d{1,2})\s*[\.\)]?\s*(?:\(?([a-d])\)?)?[\.\s:]+([^\n]+(?:\n[^\n]+)*?)?(?=(?:(?:Q(?:UESTION)?\.?\s*)?\d{1,2}\s*[\.\)]?\s*(?:\(?[a-d]\)?)?[\.\s:]+)|(?:MODULE|UNIT|\Z|OR))",
        mod_text,
        re.IGNORECASE
    ))

    for m in q_matches:
        q_num = m.group(1)
        sub_part = m.group(2) or "a"
        q_text = (m.group(3) or "").strip()

        # Extract marks if present, e.g. "(10 Marks)", "[08 Marks]", "10"
        marks = 10
        marks_match = re.search(r"\(?(\d{1,2})\s*(?:Marks|marks|M)?\)?\s*$", q_text, re.IGNORECASE)
        if marks_match:
            try:
                marks = int(marks_match.group(1))
            except ValueError:
                marks = 10
            # Clean marks from text
            q_text = re.sub(r"\(?\d{1,2}\s*(?:Marks|marks|M)?\)?\s*$", "", q_text, flags=re.IGNORECASE).strip()

        if len(q_text) > 15:
            full_q_num = f"{q_num}.{sub_part}"
            questions.append({
                "module": module_num,
                "question_number": full_q_num,
                "text": q_text,
                "marks": marks,
                "sub_parts": [full_q_num]
            })

    return questions


def _parse_numbered_questions(text: str) -> List[Dict[str, Any]]:
    questions = []
    # VTU standard: Q1, Q2 (Mod 1); Q3, Q4 (Mod 2); Q5, Q6 (Mod 3); Q7, Q8 (Mod 4); Q9, Q10 (Mod 5)
    pattern = r"(?:^|\n)\s*(?:Q\.?\s*)?([1-9]|10)\s*[\.\)]\s*(?:\(?([a-d])\)?)?[\.\s:]+(.+?)(?=(?:\n\s*(?:Q\.?\s*)?(?:[1-9]|10)\s*[\.\)])|\Z|OR)"
    for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
        q_num_int = int(match.group(1))
        sub_letter = match.group(2) or "a"
        raw_content = match.group(3).strip()
        mod_num = min(5, max(1, (q_num_int + 1) // 2))

        # Extract marks
        marks = 10
        marks_match = re.search(r"\(?(\d{1,2})\s*(?:Marks|marks|M)?\)?\s*$", raw_content, re.IGNORECASE)
        if marks_match:
            try:
                marks = int(marks_match.group(1))
            except ValueError:
                marks = 10
            raw_content = re.sub(r"\(?\d{1,2}\s*(?:Marks|marks|M)?\)?\s*$", "", raw_content, flags=re.IGNORECASE).strip()

        if len(raw_content) > 15:
            questions.append({
                "module": mod_num,
                "question_number": f"{q_num_int}.{sub_letter}",
                "text": raw_content,
                "marks": marks,
                "sub_parts": [f"{q_num_int}.{sub_letter}"]
            })

    return questions


def _fallback_heuristic_questions(text: str) -> List[Dict[str, Any]]:
    """Split sentences that look like questions into 5 modules."""
    questions = []
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 20]
    question_candidates = [
        line for line in lines
        if any(w in line.lower() for w in ["explain", "define", "what is", "compare", "write", "derive", "differentiate", "discuss", "illustrate", "calculate", "prove"])
    ]

    for i, candidate in enumerate(question_candidates[:10]):
        mod = min(5, (i // 2) + 1)
        questions.append({
            "module": mod,
            "question_number": f"{i+1}.a",
            "text": candidate,
            "marks": 10,
            "sub_parts": [f"{i+1}.a"]
        })
    return questions


async def extract_questions_with_gemini(text: str, course_code: str) -> Optional[List[Dict[str, Any]]]:
    """Parse questions module-wise using Gemini structured output."""
    client = get_gemini_client()
    if not client:
        return None

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = f"""
You are an expert VTU Examination Paper Parser.
Parse the following VTU question paper text for course code '{course_code}'.
Extract all questions module by module (Module 1 through Module 5).
For each question, output:
- "module": int (1, 2, 3, 4, or 5)
- "question_number": str (e.g. "1.a", "2.b")
- "text": str (full, clear text of the question or subquestion)
- "marks": int (marks assigned, usually between 4 and 10, default 10)
- "sub_parts": list of strings (e.g. ["1.a"])

Paper Text:
\"\"\"{text[:10000]}\"\"\"

Return ONLY a valid JSON array of question objects.
Example:
[
  {{"module": 1, "question_number": "1.a", "text": "Explain linear and non-linear data structures with examples.", "marks": 10, "sub_parts": ["1.a"]}}
]
"""
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        data = json.loads(response.text.strip())
        if isinstance(data, list) and len(data) > 0:
            cleaned = []
            for item in data:
                if isinstance(item, dict) and "module" in item and "text" in item:
                    cleaned.append({
                        "module": int(item.get("module", 1)),
                        "question_number": str(item.get("question_number", "1.a")),
                        "text": str(item.get("text", "")).strip(),
                        "marks": int(item.get("marks", 10)),
                        "sub_parts": item.get("sub_parts", [str(item.get("question_number", "1.a"))])
                    })
            return cleaned
    except Exception as exc:
        logger.warning(f"Gemini structured extraction failed, falling back to rule-based: {exc}")

    return None


async def extract_questions_from_pdf_data(pdf_bytes: bytes, course_code: str, scheme: Optional[str] = None) -> Tuple[bool, str, Optional[str], List[Dict[str, Any]], str]:
    """Complete extraction pipeline: text extraction -> validation -> module-wise question extraction.

    Returns:
    (is_valid, validation_msg, detected_session, questions_list, raw_text)
    """
    raw_text = extract_raw_text_from_pdf(pdf_bytes)
    if not raw_text or len(raw_text.strip()) < 30:
        return False, "Could not extract sufficient text from PDF (scanned or corrupted file).", None, [], ""

    is_valid, reason, session = validate_vtu_paper(raw_text, course_code, scheme)
    if not is_valid:
        return False, reason, session, [], raw_text

    # Extract questions: try Gemini first if available, then fallback to rule-based
    questions = await extract_questions_with_gemini(raw_text, course_code)
    if not questions:
        questions = extract_questions_rule_based(raw_text)

    return True, "Validated and parsed successfully.", session or "Exam Session", questions, raw_text
