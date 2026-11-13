"""Script to generate realistic VTU exam paper PDFs for seed data."""
import json
from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parent.parent
SEEDS_PATH = BASE_DIR / "data" / "seeds" / "seed_papers.json"
SEEDS_DIR = BASE_DIR / "data" / "seeds"

def generate_seeds():
    with open(SEEDS_PATH, "r", encoding="utf-8") as f:
        papers = json.load(f)

    for p in papers:
        pdf_filename = f"{p['id']}.pdf"
        pdf_path = SEEDS_DIR / pdf_filename
        doc = fitz.open()

        # Page 1: Header + Modules 1, 2, 3
        page1 = doc.new_page(width=595, height=842)  # A4
        y = 40
        page1.insert_text((40, y), "USN:  |__|__|__|__|__|__|__|__|__|__|", fontsize=11, fontname="helv")
        y += 25
        page1.insert_text((130, y), "VISVESVARAYA TECHNOLOGICAL UNIVERSITY, BELAGAVI", fontsize=12, fontname="hebo")
        y += 18
        sem_text = "Third Semester B.E. Degree Examination" if p.get("semester") == 3 else "Fifth Semester B.E. Degree Examination"
        page1.insert_text((160, y), f"{sem_text}, {p['exam_session']}", fontsize=11, fontname="hebo")
        y += 18
        page1.insert_text((40, y), f"Course Code: {p['course_code']}", fontsize=11, fontname="hebo")
        page1.insert_text((400, y), f"Scheme: {p.get('scheme', '2022')}", fontsize=11, fontname="helv")
        y += 16
        page1.insert_text((40, y), f"Title: {p.get('course_title', '')}", fontsize=10, fontname="helv")
        y += 16
        page1.insert_text((40, y), "Time: 3 Hours                                                                          Max. Marks: 100", fontsize=10, fontname="hebo")
        y += 14
        page1.draw_line(fitz.Point(40, y), fitz.Point(555, y))
        y += 15
        page1.insert_text((40, y), "Note: Answer any FIVE full questions, choosing ONE full question from each module.", fontsize=9, fontname="helv")
        y += 20

        questions = p.get("questions", [])
        for q in questions:
            mod = q.get("module", 1)
            if mod <= 3:
                q["page_number"] = 1
                if y > 780:
                    y = 50
                q_num = q.get("question_number", "")
                text = q.get("text", "")
                marks = q.get("marks", 10)
                header_str = f"Module {mod} - Q{q_num} [{marks} Marks]"
                page1.insert_text((40, y), header_str, fontsize=10, fontname="hebo")
                y += 14
                words = text.split()
                line = ""
                for w in words:
                    if len(line) + len(w) + 1 > 75:
                        page1.insert_text((55, y), line, fontsize=9, fontname="helv")
                        y += 12
                        line = w
                    else:
                        line = f"{line} {w}".strip()
                if line:
                    page1.insert_text((55, y), line, fontsize=9, fontname="helv")
                    y += 16

        page1.insert_text((280, 820), "Page 1 of 2", fontsize=9, fontname="helv")

        # Page 2: Modules 4, 5
        page2 = doc.new_page(width=595, height=842)
        y = 50
        page2.insert_text((40, y), f"{p['course_code']} - {p['exam_session']} (Continued)", fontsize=11, fontname="hebo")
        y += 10
        page2.draw_line(fitz.Point(40, y), fitz.Point(555, y))
        y += 20

        for q in questions:
            mod = q.get("module", 1)
            if mod >= 4:
                q["page_number"] = 2
                q_num = q.get("question_number", "")
                text = q.get("text", "")
                marks = q.get("marks", 10)
                header_str = f"Module {mod} - Q{q_num} [{marks} Marks]"
                page2.insert_text((40, y), header_str, fontsize=10, fontname="hebo")
                y += 14
                words = text.split()
                line = ""
                for w in words:
                    if len(line) + len(w) + 1 > 75:
                        page2.insert_text((55, y), line, fontsize=9, fontname="helv")
                        y += 12
                        line = w
                    else:
                        line = f"{line} {w}".strip()
                if line:
                    page2.insert_text((55, y), line, fontsize=9, fontname="helv")
                    y += 18

        page2.insert_text((280, 820), "Page 2 of 2", fontsize=9, fontname="helv")

        doc.save(str(pdf_path))
        doc.close()

        # Relative path from backend or absolute path
        p["file_path"] = str(pdf_path.resolve())

    with open(SEEDS_PATH, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2)

    print(f"Generated {len(papers)} seed PDFs successfully.")

if __name__ == "__main__":
    generate_seeds()
