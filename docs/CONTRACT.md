# API & Architecture Contract: Student Study Planner & Reminder Assistant (VTU)

## 1. Overview
This document defines the strict API contract, data schemas, and interface boundaries between Frontend and Backend.

---

## 2. VTU Academic Catalog Schema

### `GET /api/catalog`
Returns available branches, years, semesters, schemes, and courses.

#### Response `200 OK`
```json
{
  "university": "Visvesvaraya Technological University (VTU)",
  "schemes": ["2022", "2021", "2018"],
  "branches": [
    {
      "code": "CSE",
      "name": "Computer Science & Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "ISE",
      "name": "Information Science & Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "AIML",
      "name": "Artificial Intelligence & Machine Learning",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "AIDS",
      "name": "Artificial Intelligence & Data Science",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "ECE",
      "name": "Electronics & Communication Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "EEE",
      "name": "Electrical & Electronics Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "ME",
      "name": "Mechanical Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "CV",
      "name": "Civil Engineering",
      "semesters": [1, 2, 3, 4, 5, 6, 7, 8]
    },
    {
      "code": "FY-CYCLE",
      "name": "First Year Physics/Chemistry Cycle",
      "semesters": [1, 2]
    }
  ],
  "courses": [
    {
      "code": "BCS301",
      "title": "Mathematics for Computer Science",
      "branch": "CSE",
      "semester": 3,
      "scheme": "2022"
    },
    {
      "code": "BCS302",
      "title": "Digital Design and Computer Organization",
      "branch": "CSE",
      "semester": 3,
      "scheme": "2022"
    },
    {
      "code": "BCS303",
      "title": "Operating Systems",
      "branch": "CSE",
      "semester": 3,
      "scheme": "2022"
    },
    {
      "code": "BCS304",
      "title": "Data Structures and Applications",
      "branch": "CSE",
      "semester": 3,
      "scheme": "2022"
    },
    {
      "code": "21CS52",
      "title": "Computer Networks and Security",
      "branch": "CSE",
      "semester": 5,
      "scheme": "2021"
    },
    {
      "code": "21CS54",
      "title": "Automata Theory and Computability",
      "branch": "CSE",
      "semester": 5,
      "scheme": "2021"
    },
    {
      "code": "18CS61",
      "title": "System Software and Compilers",
      "branch": "CSE",
      "semester": 6,
      "scheme": "2018"
    }
  ]
}
```

---

## 3. Notes Upload Schema

### `POST /api/notes/upload`
Multipart form upload of a PDF file (max 20MB).

#### Form Fields:
- `file`: Binary PDF
- `course_code`: string (e.g. "BCS304")
- `scheme`: string (e.g. "2022")

#### Response `200 OK`
```json
{
  "notes_id": "notes_8f7b2c",
  "filename": "Unit1-3_OS_Notes.pdf",
  "file_size": 1542000,
  "pages_count": 28,
  "detected_modules": [1, 2, 3],
  "message": "Successfully parsed 28 pages of notes."
}
```

---

## 4. Question Papers Ingestion & Repetition

### `POST /api/papers/fetch`
Trigger asynchronous background web search and ingestion.

#### Request Body
```json
{
  "course_code": "BCS304",
  "course_title": "Data Structures and Applications",
  "scheme": "2022"
}
```

#### Response `202 Accepted`
```json
{
  "job_id": "job_d91a4b",
  "status": "in_progress",
  "message": "Started fetching question papers from public repositories."
}
```

### `GET /api/papers/fetch/{job_id}`
Check progress of paper discovery and extraction.

#### Response `200 OK`
```json
{
  "job_id": "job_d91a4b",
  "status": "completed", // "in_progress", "completed", "failed"
  "progress_pct": 100,
  "message": "Found and validated 4 papers.",
  "papers_found": 4,
  "papers_validated": 4,
  "errors": []
}
```

### `GET /api/papers`
Query cached papers from database.
- Query params: `course_code=BCS304`, `scheme=2022`

#### Response `200 OK`
```json
[
  {
    "id": "qp_01",
    "course_code": "BCS304",
    "scheme": "2022",
    "exam_session": "Feb/Mar 2023",
    "source_url": "https://vtu.ac.in/model-qp/bcs304.pdf",
    "status": "validated",
    "questions_count": 10,
    "fetched_at": "2026-11-13T10:00:00Z"
  }
]
```

### `POST /api/papers/upload`
Manual upload of a question paper PDF for the library.
- Form fields: `file`, `course_code`, `scheme`, `branch`, `semester`, `exam_session`.

---

## 5. Important Questions Extraction

### `POST /api/important-questions`
Compute canonical question clusters and repetition counts across cached papers.

#### Request Body
```json
{
  "course_code": "BCS304",
  "scheme": "2022",
  "selected_modules": [1, 2, 3]
}
```

#### Response `200 OK`
```json
{
  "course_code": "BCS304",
  "scheme": "2022",
  "total_papers_analyzed": 4,
  "exam_sessions": ["Jan/Feb 2023", "June/July 2023", "Jan/Feb 2024", "June/July 2024"],
  "is_reliable": true,
  "message": "Based on 4 question papers",
  "modules": [
    {
      "module": 1,
      "questions": [
        {
          "id": "iq_01",
          "canonical_question": "Explain linear and non-linear data structures with examples. Distinguish between static and dynamic memory allocation.",
          "module": 1,
          "repetition_count": 4,
          "repetition_label": "4 times",
          "sessions": ["Jan/Feb 2023", "June/July 2023", "Jan/Feb 2024", "June/July 2024"],
          "marks": 10
        }
      ]
    }
  ]
}
```

---

## 6. Study Plan Generation

### `POST /api/plan`
Generate a deterministic timetable with AI topic effort estimation and answers.

#### Request Body
```json
{
  "course_code": "BCS304",
  "course_title": "Data Structures and Applications",
  "branch": "CSE",
  "semester": 3,
  "scheme": "2022",
  "num_modules": 3,
  "num_days": 4,
  "only_important_questions": true,
  "notes_id": "notes_8f7b2c" // optional
}
```

#### Response `200 OK`
```json
{
  "plan_id": "plan_77a9c1",
  "course_code": "BCS304",
  "course_title": "Data Structures and Applications",
  "num_days": 4,
  "num_modules": 3,
  "is_heavy_plan": false,
  "heavy_warning": null,
  "created_at": "2026-11-13T10:15:00Z",
  "days": [
    {
      "day_number": 1,
      "date_label": "Day 1 (Today)",
      "total_study_minutes": 320,
      "items": [
        {
          "id": "item_d1_01",
          "type": "study",
          "module": 1,
          "title": "Linear vs Non-Linear Data Structures & Dynamic Memory",
          "start_time": "09:00",
          "end_time": "10:15",
          "duration_minutes": 75,
          "answer_id": "ans_01",
          "is_completed": false
        },
        {
          "id": "item_d1_02",
          "type": "break",
          "module": null,
          "title": "Short Break",
          "start_time": "10:15",
          "end_time": "10:30",
          "duration_minutes": 15,
          "answer_id": null,
          "is_completed": false
        }
      ]
    }
  ],
  "answers": {
    "ans_01": {
      "id": "ans_01",
      "question_or_topic": "Linear vs Non-Linear Data Structures",
      "module": 1,
      "content": "A linear data structure organizes data sequentially...",
      "source_type": "notes", // "notes" | "web" | "curriculum_grounded"
      "source_attribution": "Page 4-6 of Unit1-3_OS_Notes.pdf",
      "source_urls": []
    }
  }
}
```

### `PATCH /api/plan/{id}/items/{item_id}`
Toggle completion status.

#### Request Body
```json
{
  "is_completed": true
}
```

#### Response `200 OK`
```json
{
  "item_id": "item_d1_01",
  "is_completed": true
}
```
