---
name: vtu-paper-ingestion
description: Patterns for searching, downloading, validating, deduplicating and caching VTU previous exam question papers
---

# VTU Paper Ingestion Skill

This skill guides the discovery, validation, and structured extraction of Visvesvaraya Technological University (VTU) previous semester question papers.

## 1. Web Search Strategy
- Query formulation:
  - `"<course_code> VTU question paper"`
  - `"<course_code> <course_title> VTU previous question paper"`
  - `"<course_code> <scheme> scheme VTU question paper filetype:pdf"`
  - `"<course_code> model question paper VTU"`
- Domains to prioritize: `vtu.ac.in`, `vturesource.com`, `takeitsmart.in`, `azdocuments.in`, `vtupulse.com`, and open university repositories.
- Only fetch openly accessible files. Discard pages requiring authentication, paywalls, or captcha challenges.

## 2. Rate Limiting & Ethics
- Add a 1 to 2 second delay between HTTP requests.
- Identify requests with user agent: `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) VTUStudentAssistant/1.0`.
- Timeout per request: 12 seconds max. Cap downloaded PDF size at 25MB.
- Check robots.txt or skip paths that are explicitly blocked.

## 3. Strict Paper Validation Rules
A downloaded PDF is ONLY valid if:
1. **Course Code Match**: The exact course code (e.g. `BCS301`, `21CS52`, `18CS61`) is detected in the PDF text (case-insensitive, accounting for common whitespace/hyphen differences).
2. **VTU Authenticity**: Header keywords like "Visvesvaraya Technological University" or "VTU" or "USN" and "Time: 3 Hours" / "Max. Marks: 100" (or 50) exist.
3. **Session Identification**: Exam session and year extracted (e.g., "Jan/Feb 2023", "June/July 2022", "Dec 2023/Jan 2024").
4. **Scheme Verification**: Check if the scheme matches or is compatible (e.g., 2018, 2021, 2022).

## 4. Question Extraction & Repetition Analysis
- Extract all questions module by module (Module 1 through Module 5).
- Structure: `{module: int, question_number: str, text: str, marks: int, sub_parts: list}`.
- Repetition Clustering:
  - Canonical question extraction: group semantically equivalent questions.
  - Count = Number of DISTINCT exam sessions the question appeared in across validated papers.
  - NEVER fabricate or assume counts. If N < 2 papers found, honestly inform the user.
