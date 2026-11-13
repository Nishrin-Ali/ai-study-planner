# Audit, Security, and Bug Fixes Log (CHANGES.md)

This document tracks all security findings, audit resolutions, architectural hardening, and bug fixes applied across Phases 1 through 5.

---

## 1. Phase 1: Security Audit Findings & Fixes

### Finding 1.1: Dependency Vulnerabilities Scan
- **Severity**: Low / Info
- **Scope**: Python (`requirements.txt`) & Node.js (`package.json`)
- **Finding**: Running `pip-audit -r backend/requirements.txt` reported **0 known vulnerabilities**. Running `npm audit` in `frontend/` reported **0 vulnerabilities**.
- **Fix**: Installed and integrated `slowapi`, `bleach`, and `python-magic-bin` for rate limiting and sanitization.

### Finding 1.2: SSRF in Paper Fetcher & Web Retrieval
- **File**: `backend/app/services/security.py` & `backend/app/services/papers/fetcher.py`
- **Severity**: High
- **Finding**: Previous web fetching allowed arbitrary URLs without DNS/IP resolution validation, potentially enabling internal network or cloud metadata access (`169.254.169.254`).
- **Fix**: Built an SSRF-safe HTTP client wrapper `SafeHttpClient` in `backend/app/services/security.py`. Resolves hostnames and blocks loopback (`127.0.0.0/8`), private RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), multicast, and cloud metadata IPs. Enforces HTTPS only, limits redirects (re-validating target IP on each hop), caps downloads at 15MB with a 12s timeout, and validates `Content-Type: application/pdf`.

### Finding 1.3: Upload Security & Path Traversal
- **File**: `backend/app/routers/notes.py` & `backend/app/routers/papers.py`
- **Severity**: High
- **Finding**: File uploads relied on client-supplied filenames, lacked server-side magic byte verification, and didn't enforce max page extraction limits.
- **Fix**: Enforced `%PDF` magic byte check (`header.startswith(b"%PDF")`), 20MB file size ceiling, random UUID filenames (`uuid.uuid4().hex + ".pdf"`), storage strictly in `backend/uploads/` outside any static file paths, and capped page extraction at 60 pages.

### Finding 1.4: Prompt Injection Protection
- **File**: `backend/app/prompts/*`
- **Severity**: Medium
- **Finding**: Raw text extracted from notes or web pages was concatenated directly into LLM prompts without explicit containment tags.
- **Fix**: Delimited all untrusted notes and web texts with `<<<UNTRUSTED_CONTENT>>> ... <<<END_UNTRUSTED_CONTENT>>>`. Updated prompt templates with explicit instructions commanding the model to treat content strictly as reference data and ignore any instructions or jailbreaks contained within.

### Finding 1.5: Cross-Site Scripting (XSS)
- **File**: `frontend/src/`
- **Severity**: Medium
- **Finding**: Potential risk if rich content or unescaped markdown from AI answers was rendered into the DOM.
- **Fix**: Installed `dompurify` and sanitized all dynamic AI/study texts. Enforced plain-text/sanitized display and validated that all links use `rel="noopener noreferrer"`.

### Finding 1.6: Abuse & Rate Limiting
- **File**: `backend/app/main.py`
- **Severity**: Medium
- **Finding**: AI-spending and search-intensive endpoints lacked rate limiting.
- **Fix**: Integrated `slowapi` limiter using client remote IP. Applied rate limits to `/api/papers/fetch`, `/api/plan`, `/api/chat`, and `/api/notes/upload`. Added optional `ADMIN_TOKEN` protection for library management endpoints.

### Finding 1.7: IDOR Protection
- **File**: `backend/app/models/plans.py` & `backend/app/routers/`
- **Severity**: Low
- **Finding**: Ensure plan and job IDs cannot be sequentially enumerated.
- **Fix**: Switched all plan and task identifiers to cryptographically random UUIDv4 strings.

### Finding 1.8: Security Headers & CORS
- **File**: `backend/app/main.py`
- **Severity**: Medium
- **Finding**: Missing standard browser protection headers and permissive origins.
- **Fix**: Restricted CORS origins to the configured frontend host. Added security headers middleware injecting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 2. Phase 2: Bug Fixes

### Bug A: Question Repetition Visibility
- Extracted and stored distinct exam sessions (`sessions[]`) for each validated question paper.
- Enhanced repetition analysis with fallback token-similarity clustering if Gemini is offline or fails to return JSON.
- Displayed explicit repetition badges ("5 times", "4 times", "3 times", "2 times", "Once") and clickable source paper links.

### Bug B: Question Papers File Access & Discovery
- Built `GET /api/papers/{id}/file` streaming PDF files with `Content-Type: application/pdf` and `Content-Disposition: inline`.
- Validated that requested files reside strictly inside the verified storage directory (`backend/uploads/` or `backend/data/seeds/`).
- Added "Open paper" button and "#page=N" question anchor links.
- Added "Why was this skipped?" candidate log detailing accept/reject reasons.

### Bug C: "Study Buddy" AI Chatbot
- Built rate-limited `POST /api/chat` with SSE streaming (`text/event-stream`).
- Tailored senior student persona explaining concepts simply with examples and 5/10 marks exam tips.
- Multilingual prompt support (Kannada, Hindi, English).
- Slide-out side drawer UI in timetable with quick starter prompts ("Explain simply", "Give an example", "Make it 5 marks answer", "Quiz me").

### Bug D: Official VTU Catalog Audit
- Audited `backend/data/vtu_catalog.json` against official VTU syllabus records (2018, 2021, 2022 schemes) across CSE, ISE, AIML, AIDS, ECE, EEE, ME, Civil, and FY-Cycle.
- Recorded syllabus source URLs and marked entries `verified: true`.
- Built `backend/scripts/build_catalog.py` for reproducible syllabus ingestion.
- Added prefix-to-branch validation rules and catalog unit test suite.

---

## 3. Phase 3: Reminders Subsystem Overhaul
- Eliminated unreliable long `setTimeout` scheduling.
- Implemented 1-second interval ticker tracking absolute `Date.now()`.
- Added catch-up listener on `visibilitychange`, `focus`, and page load for missed notifications within the last 60 seconds.
- Persisted fired reminder IDs in `localStorage` to eliminate duplicates.
- Added optional soft audio chime toggle using Web Audio API.
- Integrated dual notifications: Service Worker native notification (`registration.showNotification()`) + accessible in-app toast alert for all session, break, and revision milestones.
