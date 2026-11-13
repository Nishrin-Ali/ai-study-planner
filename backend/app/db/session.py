"""Database session and SQLite management."""
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "vtu_planner.db"
SEED_FILE = DB_DIR / "seeds" / "seed_papers.json"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables and seed genuine data if empty."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS question_papers (
                    id TEXT PRIMARY KEY,
                    course_code TEXT NOT NULL,
                    course_title TEXT,
                    scheme TEXT NOT NULL,
                    branch TEXT,
                    semester INTEGER,
                    exam_session TEXT NOT NULL,
                    source_url TEXT,
                    file_path TEXT,
                    status TEXT NOT NULL DEFAULT 'validated',
                    questions_count INTEGER DEFAULT 0,
                    questions_json TEXT,
                    raw_text TEXT,
                    fetched_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qp_course_scheme 
                ON question_papers(course_code, scheme);
            """)

            # Seed pre-configured papers if not already present
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM question_papers")
            count = cursor.fetchone()[0]

            if count == 0 and SEED_FILE.exists():
                with open(SEED_FILE, "r", encoding="utf-8") as f:
                    seed_papers = json.load(f)
                for paper in seed_papers:
                    conn.execute("""
                        INSERT OR REPLACE INTO question_papers (
                            id, course_code, course_title, scheme, branch, semester,
                            exam_session, source_url, file_path, status,
                            questions_count, questions_json, raw_text, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        paper.get("id"),
                        paper.get("course_code"),
                        paper.get("course_title"),
                        paper.get("scheme"),
                        paper.get("branch", "CSE"),
                        paper.get("semester", 3),
                        paper.get("exam_session"),
                        paper.get("source_url"),
                        paper.get("file_path"),
                        paper.get("status", "validated"),
                        paper.get("questions_count", len(paper.get("questions", []))),
                        json.dumps(paper.get("questions", []), ensure_ascii=False),
                        paper.get("raw_text", ""),
                    ))
    finally:
        conn.close()


def query_papers(course_code: Optional[str] = None, scheme: Optional[str] = None) -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM question_papers WHERE 1=1"
        params: List[Any] = []
        if course_code:
            query += " AND UPPER(course_code) = ?"
            params.append(course_code.strip().upper())
        if scheme:
            query += " AND scheme = ?"
            params.append(scheme.strip())
        query += " ORDER BY fetched_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d.get("questions_json"):
                try:
                    d["questions"] = json.loads(d["questions_json"])
                except Exception:
                    d["questions"] = []
            else:
                d["questions"] = []
            results.append(d)
        return results
    finally:
        conn.close()


def save_paper(paper: Dict[str, Any]) -> str:
    init_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO question_papers (
                    id, course_code, course_title, scheme, branch, semester,
                    exam_session, source_url, file_path, status,
                    questions_count, questions_json, raw_text, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                paper["id"],
                paper["course_code"].strip().upper(),
                paper.get("course_title", ""),
                paper["scheme"].strip(),
                paper.get("branch"),
                paper.get("semester"),
                paper["exam_session"].strip(),
                paper.get("source_url"),
                paper.get("file_path"),
                paper.get("status", "validated"),
                paper.get("questions_count", len(paper.get("questions", []))),
                json.dumps(paper.get("questions", []), ensure_ascii=False),
                paper.get("raw_text", ""),
            ))
        return paper["id"]
    finally:
        conn.close()
