# Student Study Planner & Reminder Assistant (VTU)

A complete, working web application built exclusively for **Visvesvaraya Technological University (VTU)** students. It generates deterministic, realistic study timetables, discovers and validates previous year question papers from the web, computes genuine repetition counts, synthesizes grounded answers, and delivers browser and in-app reminders.

---

## 1. Features
- **VTU Academic Details Selection**:
  - University: Fixed to VTU.
  - Branches: CSE, ISE, AIML, AIDS, ECE, EEE, ME, Civil, and 1st Year Physics/Chemistry cycle.
  - Years 1–4 with dependent Semesters (1–8).
  - VTU Schemes: 2022, 2021, and 2018.
  - Searchable Course combobox + custom course code entry (e.g. `BCS304`).
- **Plan Configuration**:
  - Clean segmented selectors: 1–5 Modules, 1–10 Days.
  - "Only Important Questions" mode.
- **VTU Question Paper Ingestion & Analysis**:
  - Searches public web sources for past semester question papers using Tavily Search API.
  - Strict validation: checks course code, university headers, marks, and exam session in PDF text.
  - Caches validated papers in SQLite (`backend/vtu_planner.db`).
  - Clusters semantically equivalent questions using Gemini structured output and counts distinct exam sessions.
  - **Data Honesty**: Repetition counts come strictly from validated papers. If fewer than 2 papers are found, the app informs the student honestly.
- **Library (`/library`)**:
  - View cached papers with source links.
  - Trigger live background web search.
  - Manual question paper PDF upload with metadata tagging.
- **Faculty Notes (Optional)**:
  - Option A: Upload class notes (PDF up to 20MB); answers are extracted and grounded strictly in the notes.
  - Option B: Discovers VTU curriculum resources online and synthesizes grounded answers with citations.
- **Deterministic Timetable Engine**:
  - Sessions ~45–80 mins, 10–15 min breaks, 30–45 min midday lunch (~13:00).
  - Preserves module contiguity (Module 1, then Module 2, etc.).
  - Workload spread evenly across days; Day N reserved for full syllabus revision when days > 1.
  - Automatically flags heavy plans (> 6.5 study hours/day).
  - Expandable items with grounded answers and source references; persistent task completion.
- **Browser Reminders & Status Bar**:
  - Web Notification API via Service Worker (`/sw.js`) requested only on user click.
  - In-app toast alerts fallback for session starts, session ends, and breaks.
  - Sticky "Now / Next up" status bar with countdown.
  - "Send test reminder" button.
- **Clean Human-Crafted Minimal UI**:
  - Single calm indigo accent (`#4F46E5`), Slate typography, 4/8px spacing grid, bordered cards, zero gradients/glow/blobs.

---

## 2. Tech Stack
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons, React Router.
- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, SQLite, Pydantic v2.
- **AI**: Google Gemini API via `google-genai` SDK (`gemini-2.5-flash`).
- **Web Retrieval**: Tavily Search API, `httpx`, `trafilatura`.
- **PDF Extraction**: PyMuPDF (`fitz`), with Gemini Multimodal fallback for scanned documents.

---

## 3. Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Backend Setup
1. Open a terminal in the root directory:
   ```bash
   cd backend
   ```
2. Configure environment variables in `backend/.env` (copied from `.env.example`):
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
   *Note: If API keys are omitted, the backend starts gracefully and utilizes pre-seeded verified VTU curriculum data without crashing.*
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI backend:
   ```bash
   # From the project root
   $env:PYTHONPATH = "backend"
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Frontend Setup
1. Open a new terminal in `frontend`:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173/` in your browser.

---

## 4. Running Tests
Run the deterministic scheduler and API test suite:
```bash
$env:PYTHONPATH = "backend"
python -m pytest backend/tests
```
All 11 unit & integration tests verify session timing, breaks, lunch placement, module continuity, heavy plan detection, and API endpoints.

---

## 5. Web Paper Fetcher: How It Works & Limits
1. When "Only Important Questions" is enabled, the backend checks `vtu_planner.db` for cached papers matching the course code and scheme.
2. If papers are missing, it invokes Tavily Search API with queries like `"<course code> VTU question paper"`.
3. It downloads openly accessible PDFs, validates that the course code and VTU headers exist in the text, and parses the exam session.
4. **Limits & Ethics**:
   - VTU does not provide a public authenticated API. Web discovery depends on public educational repositories.
   - Some newly introduced subjects in recent schemes (e.g., 2022 scheme electives) may have few openly available past papers online.
   - The app guarantees **data honesty**: repetition counts are never hallucinated. When fewer than 2 papers are found, students can upload papers directly via `/library`.

---

## 6. Demo Script (Quick Walkthrough)
1. Navigate to `http://localhost:5173/`.
2. **Step 1**: Select **CSE**, **2nd Year**, **Semester 3**, **2022 Scheme**, and **BCS304** (Data Structures and Applications). Click Continue.
3. **Step 2**: Select **3 Modules** and **4 Days**. Check **Only Important Questions**. Watch the live paper discovery and repetition analysis report. Click Continue.
4. **Step 3**: Select **Continue Without Upload** (or upload a sample PDF notes file). Click **Generate Timetable**.
5. **Step 4**:
   - Inspect the day tabs (Days 1–4). Day 4 is dedicated to comprehensive revision.
   - Click **Enable Reminders** to authorize browser notifications.
   - Click **Test Reminder** to view the in-app break alert banner.
   - Expand any study block to inspect the grounded answer. Check off completed items.
6. Visit `http://localhost:5173/library` to view all cached papers and upload new ones.
