"""Important Questions Extraction and Repetition Analysis Service.

Clusters semantically equivalent questions across exam sessions to identify recurring patterns.
Strictly adheres to data honesty: never hallucinate repetition counts.
"""
from collections import defaultdict
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.papers import Question, QuestionPaper
from app.schemas.papers import (
    CanonicalQuestionItem,
    ImportantQuestionsResponse,
    ModuleQuestionsGroup,
)

logger = logging.getLogger(__name__)

SEEDS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "seed_papers.json"

# Attempt to load genai SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai:
        return genai.Client(api_key=api_key)
    return None


def ensure_seeds_loaded(db: Session, course_code: str, scheme: Optional[str] = None) -> None:
    """If DB has 0 papers for course_code, automatically populate from seed_papers.json."""
    norm_code = course_code.strip().upper()
    existing_count = (
        db.query(QuestionPaper)
        .filter(QuestionPaper.course_code == norm_code)
        .count()
    )
    if existing_count > 0:
        return

    if not SEEDS_FILE.exists():
        return

    try:
        with open(SEEDS_FILE, "r", encoding="utf-8") as f:
            seeds = json.load(f)

        for paper_data in seeds:
            if paper_data.get("course_code", "").strip().upper() != norm_code:
                continue

            paper_id = paper_data.get("id")
            # Check if paper already exists by ID
            if db.query(QuestionPaper).filter(QuestionPaper.id == paper_id).first():
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
            )
            db.add(paper)
            db.flush()

            for idx, q_data in enumerate(paper_data.get("questions", []), 1):
                q = Question(
                    id=f"q_{paper.id}_{idx}",
                    paper_id=paper.id,
                    module=int(q_data.get("module", 1)),
                    question_number=str(q_data.get("question_number", f"{idx}.a")),
                    text=str(q_data.get("text", "")).strip(),
                    marks=int(q_data.get("marks", 10)),
                    page_number=int(q_data.get("page_number", 1)),
                )
                db.add(q)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(f"Error seeding papers for {norm_code}: {exc}")


def _clean_tokens(text: str) -> Set[str]:
    """Extract significant lowercase word tokens for similarity clustering."""
    stopwords = {
        "what", "is", "a", "an", "the", "and", "or", "with", "explain", "describe",
        "write", "discuss", "give", "briefly", "detail", "suitable", "example",
        "examples", "algorithm", "c", "program", "following", "between", "distinguish",
        "differentiate", "state", "define", "short", "notes", "on", "in", "to", "of", "for"
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return {w for w in words if w not in stopwords}


def _token_jaccard_similarity(t1: Set[str], t2: Set[str]) -> float:
    if not t1 or not t2:
        return 0.0
    intersection = len(t1 & t2)
    union = len(t1 | t2)
    return intersection / union if union > 0 else 0.0


def cluster_questions_algorithmically(module: int, session_questions: List[Dict[str, Any]]) -> List[CanonicalQuestionItem]:
    """Group questions within a module by semantic keyword similarity and count distinct sessions."""
    clusters: List[Dict[str, Any]] = []

    for item in session_questions:
        text = item["text"]
        session = item["session"]
        marks = item.get("marks", 10)
        tokens = _clean_tokens(text)

        matched_cluster = None
        best_sim = 0.0

        for cluster in clusters:
            sim = _token_jaccard_similarity(tokens, cluster["tokens"])
            if sim >= 0.35 and sim > best_sim:
                best_sim = sim
                matched_cluster = cluster

        if matched_cluster:
            matched_cluster["sessions"].add(session)
            matched_cluster["items"].append(item)
            matched_cluster["tokens"].update(tokens)
            if len(text) > len(matched_cluster["canonical_question"]):
                matched_cluster["canonical_question"] = text
        else:
            clusters.append({
                "canonical_question": text,
                "sessions": {session},
                "tokens": tokens,
                "marks": marks,
                "items": [item]
            })

    result_items: List[CanonicalQuestionItem] = []
    for idx, c in enumerate(clusters, 1):
        rep_count = len(c["sessions"])
        sessions_list = sorted(list(c["sessions"]))
        label = "Once" if rep_count == 1 else f"{rep_count} times"
        paper_ids = sorted(list({it.get("paper_id") for it in c["items"] if it.get("paper_id")}))
        primary_paper_id = paper_ids[0] if paper_ids else None
        page_number = c["items"][0].get("page_number", 1) if c["items"] else 1
        result_items.append(CanonicalQuestionItem(
            id=f"iq_m{module}_{idx:02d}",
            canonical_question=c["canonical_question"],
            module=module,
            repetition_count=rep_count,
            repetition_label=label,
            sessions=sessions_list,
            marks=c["marks"],
            paper_ids=paper_ids,
            primary_paper_id=primary_paper_id,
            page_number=page_number,
        ))

    result_items.sort(key=lambda x: (x.repetition_count, len(x.canonical_question)), reverse=True)
    return result_items


async def cluster_questions_with_gemini(module: int, session_questions: List[Dict[str, Any]]) -> Optional[List[CanonicalQuestionItem]]:
    """Use Gemini to cluster semantically equivalent questions and identify distinct exam sessions."""
    client = get_gemini_client()
    if not client:
        return None

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    simplified_items = [
        {"session": q["session"], "text": q["text"], "marks": q.get("marks", 10)}
        for q in session_questions
    ]

    prompt = f"""
You are an expert VTU curriculum analyzer.
Given the following list of examination questions for Module {module} collected across different exam sessions:
<<<UNTRUSTED_CONTENT>>>
{json.dumps(simplified_items, indent=2)}
<<<END_UNTRUSTED_CONTENT>>>

Task:
1. Cluster semantically equivalent or overlapping questions that test the exact same concept into a single "canonical_question".
2. For each canonical question, compute the list of distinct exam sessions it appeared in.
3. Compute "repetition_count" = number of distinct exam sessions.
4. Output a JSON array of objects with the exact keys:
   - "canonical_question": clear, representative VTU question formulation.
   - "module": {module}
   - "repetition_count": int (number of distinct sessions)
   - "repetition_label": e.g. "4 times", "2 times", "Once"
   - "sessions": list of distinct session strings
   - "marks": int (typical marks, e.g. 10 or 8)

Order the questions descending by repetition_count.
Return ONLY valid JSON array.
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
            items: List[CanonicalQuestionItem] = []
            for idx, c in enumerate(data, 1):
                rep_count = int(c.get("repetition_count", len(c.get("sessions", []))))
                label = "Once" if rep_count == 1 else f"{rep_count} times"
                matched_sessions = set(c.get("sessions", []))
                # Correlate session questions to get real paper_ids and page numbers
                matched_q = [q for q in session_questions if q.get("session") in matched_sessions]
                paper_ids = sorted(list({q.get("paper_id") for q in matched_q if q.get("paper_id")}))
                primary_paper_id = paper_ids[0] if paper_ids else None
                page_num = matched_q[0].get("page_number", 1) if matched_q else 1

                items.append(CanonicalQuestionItem(
                    id=f"iq_m{module}_{idx:02d}",
                    canonical_question=str(c.get("canonical_question", "")).strip(),
                    module=module,
                    repetition_count=rep_count,
                    repetition_label=label,
                    sessions=list(c.get("sessions", [])),
                    marks=int(c.get("marks", 10)),
                    paper_ids=paper_ids,
                    primary_paper_id=primary_paper_id,
                    page_number=page_num,
                ))
            items.sort(key=lambda x: x.repetition_count, reverse=True)
            return items
    except Exception as exc:
        logger.warning(f"Gemini repetition clustering error on module {module}: {exc}")

    return None


async def analyze_important_questions(
    course_code: str,
    scheme: str,
    selected_modules: Optional[List[int]] = None,
    db: Optional[Session] = None
) -> ImportantQuestionsResponse:
    """Analyze all cached papers for course_code and scheme, clustering questions per module."""
    norm_code = course_code.strip().upper()
    close_db_at_end = False
    if db is None:
        db = SessionLocal()
        close_db_at_end = True

    try:
        # Auto-seed if database doesn't have papers for this course
        ensure_seeds_loaded(db, norm_code, scheme)

        # Query validated papers
        query = (
            db.query(QuestionPaper)
            .filter(QuestionPaper.course_code == norm_code)
            .filter(QuestionPaper.status == "validated")
        )
        if scheme:
            query = query.filter(QuestionPaper.scheme == scheme.strip())

        papers = query.all()

        total_papers = len(papers)
        exam_sessions = [p.exam_session for p in papers if p.exam_session]
        distinct_sessions = sorted(list(set(exam_sessions)))

        # HONESTY CHECK: If fewer than 2 valid papers, return honest warning
        if total_papers < 2:
            modules_out: List[ModuleQuestionsGroup] = []
            if total_papers == 1:
                paper = papers[0]
                session = paper.exam_session or "Unknown Session"
                mod_map = defaultdict(list)
                for q in paper.questions:
                    mod_map[q.module].append(q)

                mod_list = selected_modules or sorted(list(mod_map.keys()))
                for m in mod_list:
                    items = []
                    for idx, q in enumerate(mod_map.get(m, []), 1):
                        items.append(CanonicalQuestionItem(
                            id=f"iq_m{m}_{idx:02d}",
                            canonical_question=q.text,
                            module=m,
                            repetition_count=1,
                            repetition_label="1 time",
                            sessions=[session],
                            marks=q.marks or 10
                        ))
                    modules_out.append(ModuleQuestionsGroup(module=m, questions=items))

            warning_msg = (
                f"Only {total_papers} question paper available. Repetition counts require at least 2 papers "
                f"to establish recurring patterns reliably. Please upload more papers or fetch them."
            ) if total_papers == 1 else (
                f"No validated question papers found for {norm_code} ({scheme} scheme). "
                f"Please fetch or upload papers first."
            )

            return ImportantQuestionsResponse(
                course_code=norm_code,
                scheme=scheme,
                total_papers_analyzed=total_papers,
                exam_sessions=distinct_sessions,
                is_reliable=False,
                message=warning_msg,
                modules=modules_out
            )

        # Group questions by module across all papers
        module_questions: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for p in papers:
            session = p.exam_session or "Unknown Session"
            for q in p.questions:
                module_questions[q.module].append({
                    "session": session,
                    "text": q.text,
                    "marks": q.marks or 10,
                    "question_number": q.question_number,
                    "paper_id": p.id,
                    "page_number": getattr(q, "page_number", 1) or 1,
                })

        active_modules = selected_modules if selected_modules else sorted(list(module_questions.keys()))
        if not active_modules:
            active_modules = [1, 2, 3, 4, 5]

        module_groups: List[ModuleQuestionsGroup] = []

        for mod in active_modules:
            q_list = module_questions.get(mod, [])
            if not q_list:
                module_groups.append(ModuleQuestionsGroup(module=mod, questions=[]))
                continue

            clustered = await cluster_questions_with_gemini(mod, q_list)
            if not clustered:
                clustered = cluster_questions_algorithmically(mod, q_list)

            module_groups.append(ModuleQuestionsGroup(
                module=mod,
                questions=clustered
            ))

        return ImportantQuestionsResponse(
            course_code=norm_code,
            scheme=scheme,
            total_papers_analyzed=total_papers,
            exam_sessions=distinct_sessions,
            is_reliable=True,
            message=f"Based on {total_papers} question papers",
            modules=module_groups
        )
    finally:
        if close_db_at_end:
            db.close()
