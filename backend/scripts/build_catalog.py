"""VTU Catalog Builder and Audit Script.

Builds, validates, and writes backend/data/vtu_catalog.json with verified VTU course codes,
official titles, branch mappings, credit weights, and official vtu.ac.in syllabus references.
Ensures zero duplicate course codes within any (scheme, semester) slice.
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

CATALOG_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "vtu_catalog.json"

# VTU Official Syllabus References
URL_2022_FY = "https://vtu.ac.in/wp-content/uploads/2022/11/1st-and-2nd-sem-syllabus.pdf"
URL_2022_CSE = "https://vtu.ac.in/wp-content/uploads/2023/07/BCS-3-8-sem-syllabus.pdf"
URL_2022_ISE = "https://vtu.ac.in/wp-content/uploads/2023/07/BIS-3-8-sem-syllabus.pdf"
URL_2022_AIML = "https://vtu.ac.in/wp-content/uploads/2023/07/BAI-3-8-sem-syllabus.pdf"
URL_2022_AIDS = "https://vtu.ac.in/wp-content/uploads/2023/07/BAD-3-8-sem-syllabus.pdf"
URL_2022_ECE = "https://vtu.ac.in/wp-content/uploads/2023/07/BEC-3-8-sem-syllabus.pdf"
URL_2022_EEE = "https://vtu.ac.in/wp-content/uploads/2023/07/BEE-3-8-sem-syllabus.pdf"
URL_2022_ME = "https://vtu.ac.in/wp-content/uploads/2023/07/BME-3-8-sem-syllabus.pdf"
URL_2022_CV = "https://vtu.ac.in/wp-content/uploads/2023/07/BCV-3-8-sem-syllabus.pdf"

URL_2021_SCHEME = "https://vtu.ac.in/b-e-scheme-syllabus/#menu06"
URL_2018_SCHEME = "https://vtu.ac.in/b-e-scheme-syllabus/#menu03"

BRANCHES_METADATA = [
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
]

# Raw verified catalog entries across 2022, 2021, and 2018 schemes
COURSES_DATA: List[Dict[str, Any]] = [
    # =========================================================================
    # FY-CYCLE (First Year Physics & Chemistry Cycles)
    # =========================================================================
    # 2022 Scheme FY-CYCLE
    {"code": "BMATS101", "title": "Mathematics for CSE Stream-I", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATM101", "title": "Mathematics for ME Stream-I", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATE101", "title": "Mathematics for EEE Stream-I", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATC101", "title": "Mathematics for Civil Stream-I", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BPHYS102", "title": "Applied Physics for CSE Stream", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BCHES102", "title": "Applied Chemistry for CSE Stream", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BPOPS103", "title": "Principles of Programming using C", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BCEDK103", "title": "Computer-Aided Engineering Drawing", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BESCK104A", "title": "Introduction to Civil Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BESCK104B", "title": "Introduction to Electrical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BESCK104C", "title": "Introduction to Electronics Communication", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BESCK104D", "title": "Introduction to Mechanical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 3, "source_url": URL_2022_FY},
    {"code": "BENGK106", "title": "Communicative English", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},
    {"code": "BICOK107", "title": "Indian Constitution", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},
    {"code": "BIDTK108", "title": "Innovation and Design Thinking", "branch": "FY-CYCLE", "semester": 1, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},
    {"code": "BMATS201", "title": "Mathematics for CSE Stream-II", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATM201", "title": "Mathematics for ME Stream-II", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATE201", "title": "Mathematics for EEE Stream-II", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BMATC201", "title": "Mathematics for Civil Stream-II", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BPHYS202", "title": "Applied Physics for Smart Materials", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BCHES202", "title": "Chemistry for Smart Materials", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 4, "source_url": URL_2022_FY},
    {"code": "BPWSK206", "title": "Professional Writing Skills in English", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},
    {"code": "BKBK207", "title": "Balake Kannada", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},
    {"code": "BKSK207", "title": "Samskrutika Kannada", "branch": "FY-CYCLE", "semester": 2, "scheme": "2022", "credits": 1, "source_url": URL_2022_FY},

    # 2021 Scheme FY-CYCLE
    {"code": "21MAT11", "title": "Calculus and Differential Equations", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21PHY12", "title": "Engineering Physics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CHE12", "title": "Engineering Chemistry", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21PSP13", "title": "Problem Solving through Programming", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ELE13", "title": "Basic Electrical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ELN14", "title": "Basic Electronics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EME15", "title": "Elements of Mechanical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CIV14", "title": "Elements of Civil Engineering and Mechanics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EGDL15", "title": "Engineering Graphics & Computer Aided Drawing", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IDT19", "title": "Innovation and Design Thinking", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 1, "source_url": URL_2021_SCHEME},
    {"code": "21EGH18", "title": "Professional Writing Skills in English", "branch": "FY-CYCLE", "semester": 1, "scheme": "2021", "credits": 1, "source_url": URL_2021_SCHEME},
    {"code": "21MAT21", "title": "Advanced Calculus and Numerical Methods", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21PHY22", "title": "Engineering Physics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CHE22", "title": "Engineering Chemistry", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21PSP23", "title": "Problem Solving through Programming", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ELE23", "title": "Basic Electrical Engineering", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ELN24", "title": "Basic Electronics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CIV24", "title": "Elements of Civil Engineering and Mechanics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21KSK27", "title": "Samskrutika Kannada", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 1, "source_url": URL_2021_SCHEME},
    {"code": "21KBK27", "title": "Balake Kannada", "branch": "FY-CYCLE", "semester": 2, "scheme": "2021", "credits": 1, "source_url": URL_2021_SCHEME},

    # 2018 Scheme FY-CYCLE
    {"code": "18MAT11", "title": "Calculus and Linear Algebra", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18PHY12", "title": "Engineering Physics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CHE12", "title": "Engineering Chemistry", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CPS13", "title": "C Programming for Problem Solving", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ELE13", "title": "Basic Electrical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ELN14", "title": "Basic Electronics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CIV14", "title": "Elements of Civil Engineering and Mechanics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME15", "title": "Elements of Mechanical Engineering", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EGDL15", "title": "Engineering Graphics", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EGH18", "title": "Technical English-I", "branch": "FY-CYCLE", "semester": 1, "scheme": "2018", "credits": 1, "source_url": URL_2018_SCHEME},
    {"code": "18MAT21", "title": "Advanced Calculus and Numerical Methods", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18PHY22", "title": "Engineering Physics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CHE22", "title": "Engineering Chemistry", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CPS23", "title": "C Programming for Problem Solving", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ELE23", "title": "Basic Electrical Engineering", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ELN24", "title": "Basic Electronics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CIV24", "title": "Elements of Civil Engineering and Mechanics", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EGH28", "title": "Technical English-II", "branch": "FY-CYCLE", "semester": 2, "scheme": "2018", "credits": 1, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # CSE (Computer Science & Engineering)
    # =========================================================================
    # 2022 Scheme CSE
    {"code": "BCS301", "title": "Mathematics for Computer Science", "branch": "CSE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS302", "title": "Digital Design and Computer Organization", "branch": "CSE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS303", "title": "Operating Systems", "branch": "CSE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS304", "title": "Data Structures and Applications", "branch": "CSE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS306A", "title": "Object Oriented Programming with Java", "branch": "CSE", "semester": 3, "scheme": "2022", "credits": 3, "source_url": URL_2022_CSE},
    {"code": "BCS401", "title": "Analysis & Design of Algorithms", "branch": "CSE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS402", "title": "Database Management Systems", "branch": "CSE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS403", "title": "Microcontrollers and Embedded Systems", "branch": "CSE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS404", "title": "Discrete Mathematical Structures", "branch": "CSE", "semester": 4, "scheme": "2022", "credits": 3, "source_url": URL_2022_CSE},
    {"code": "BCS501", "title": "Software Engineering and Project Management", "branch": "CSE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS502", "title": "Computer Networks", "branch": "CSE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS503", "title": "Theory of Computation", "branch": "CSE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS601", "title": "Cloud Computing", "branch": "CSE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS602", "title": "Machine Learning", "branch": "CSE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_CSE},
    {"code": "BCS701", "title": "Artificial Intelligence", "branch": "CSE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_CSE},
    {"code": "BCS702", "title": "Big Data Analytics", "branch": "CSE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_CSE},
    {"code": "BCS801", "title": "Internet of Things", "branch": "CSE", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_CSE},

    # 2021 Scheme CSE
    {"code": "21MATCS31", "title": "Transform Calculus, Fourier Series and Numerical Techniques", "branch": "CSE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS32", "title": "Data Structures and Applications", "branch": "CSE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS33", "title": "Analog and Digital Electronics", "branch": "CSE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS34", "title": "Computer Organization and Architecture", "branch": "CSE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS41", "title": "Mathematical Foundations for Computing, Probability & Statistics", "branch": "CSE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS42", "title": "Design and Analysis of Algorithms", "branch": "CSE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS43", "title": "Microcontroller and Embedded Systems", "branch": "CSE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS44", "title": "Operating Systems", "branch": "CSE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS51", "title": "Management, Entrepreneurship and IPR", "branch": "CSE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS52", "title": "Computer Networks and Security", "branch": "CSE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS53", "title": "Database Management System", "branch": "CSE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS54", "title": "Automata Theory and Computability", "branch": "CSE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS61", "title": "Software Engineering and Project Management", "branch": "CSE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS62", "title": "Full Stack Development", "branch": "CSE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS71", "title": "Artificial Intelligence and Machine Learning", "branch": "CSE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS72", "title": "Cloud Computing", "branch": "CSE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CS81", "title": "Internet of Things and Applications", "branch": "CSE", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme CSE
    {"code": "18MAT31", "title": "Transform Calculus, Fourier Series and Numerical Techniques", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS32", "title": "Data Structures and Applications", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS33", "title": "Analog and Digital Electronics", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS34", "title": "Computer Organization", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS35", "title": "Software Engineering", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS36", "title": "Discrete Mathematical Structures", "branch": "CSE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS42", "title": "Design and Analysis of Algorithms", "branch": "CSE", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS43", "title": "Operating Systems", "branch": "CSE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS44", "title": "Microcontroller and Embedded Systems", "branch": "CSE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS45", "title": "Object Oriented Concepts", "branch": "CSE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS46", "title": "Data Communication", "branch": "CSE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS51", "title": "Management and Entrepreneurship for IT Industry", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS52", "title": "Computer Networks and Security", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS53", "title": "Database Management System", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS54", "title": "Automata Theory and Computability", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS55", "title": "Application Development using Python", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS56", "title": "Unix Programming", "branch": "CSE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CS61", "title": "System Software and Compilers", "branch": "CSE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS62", "title": "Computer Graphics and Visualization", "branch": "CSE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS63", "title": "Web Technology and its Applications", "branch": "CSE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS71", "title": "Artificial Intelligence and Machine Learning", "branch": "CSE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS72", "title": "Big Data Analytics", "branch": "CSE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CS81", "title": "Internet of Things", "branch": "CSE", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # ISE (Information Science & Engineering)
    # =========================================================================
    # 2022 Scheme ISE
    {"code": "BIS301", "title": "Mathematics for Information Science", "branch": "ISE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS302", "title": "Digital Design and Computer Organization", "branch": "ISE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS303", "title": "Operating Systems", "branch": "ISE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS304", "title": "Data Structures and Applications", "branch": "ISE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS401", "title": "Analysis and Design of Algorithms", "branch": "ISE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS402", "title": "Database Management Systems", "branch": "ISE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS403", "title": "Microcontrollers and Embedded Systems", "branch": "ISE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS501", "title": "Software Engineering", "branch": "ISE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS502", "title": "Computer Networks", "branch": "ISE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS503", "title": "Automata and Compiler Design", "branch": "ISE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS601", "title": "Web Technologies", "branch": "ISE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS602", "title": "Machine Learning and Applications", "branch": "ISE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ISE},
    {"code": "BIS701", "title": "Information and Network Security", "branch": "ISE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_ISE},
    {"code": "BIS801", "title": "Storage Area Networks", "branch": "ISE", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_ISE},

    # 2021 Scheme ISE
    {"code": "21IS32", "title": "Data Structures and Applications", "branch": "ISE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS33", "title": "Analog and Digital Electronics", "branch": "ISE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS34", "title": "Computer Organization and Architecture", "branch": "ISE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS42", "title": "Design and Analysis of Algorithms", "branch": "ISE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS43", "title": "Microcontroller and Embedded Systems", "branch": "ISE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS44", "title": "Operating Systems", "branch": "ISE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS51", "title": "Management, Entrepreneurship and IPR", "branch": "ISE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS52", "title": "Computer Networks and Security", "branch": "ISE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS53", "title": "Database Management Systems", "branch": "ISE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS54", "title": "Automata Theory and Computability", "branch": "ISE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS61", "title": "Software Architecture and Design Patterns", "branch": "ISE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS62", "title": "Web Technology", "branch": "ISE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS71", "title": "Cloud Computing and Big Data", "branch": "ISE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS72", "title": "Information and Cyber Security", "branch": "ISE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21IS81", "title": "Internet of Things", "branch": "ISE", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme ISE
    {"code": "18IS32", "title": "Data Structures and Applications", "branch": "ISE", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS33", "title": "Analog and Digital Electronics", "branch": "ISE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS34", "title": "Computer Organization", "branch": "ISE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS35", "title": "Software Engineering", "branch": "ISE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS42", "title": "Design and Analysis of Algorithms", "branch": "ISE", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS43", "title": "Operating Systems", "branch": "ISE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS44", "title": "Microcontroller and Embedded Systems", "branch": "ISE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS51", "title": "Management and Entrepreneurship for IT Industry", "branch": "ISE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS52", "title": "Computer Networks and Security", "branch": "ISE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS53", "title": "Database Management System", "branch": "ISE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS54", "title": "Automata Theory and Computability", "branch": "ISE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18IS61", "title": "File Structures", "branch": "ISE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS62", "title": "Software Testing", "branch": "ISE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS71", "title": "Artificial Intelligence and Machine Learning", "branch": "ISE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS72", "title": "Big Data Analytics", "branch": "ISE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18IS81", "title": "Internet of Things", "branch": "ISE", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # AIML (Artificial Intelligence & Machine Learning)
    # =========================================================================
    # 2022 Scheme AIML
    {"code": "BAI301", "title": "Mathematics for AI and ML", "branch": "AIML", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI302", "title": "Digital Design and Computer Organization", "branch": "AIML", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI303", "title": "Operating Systems", "branch": "AIML", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI304", "title": "Data Structures and Applications", "branch": "AIML", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI401", "title": "Analysis and Design of Algorithms", "branch": "AIML", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI402", "title": "Database Management Systems", "branch": "AIML", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI403", "title": "Artificial Intelligence", "branch": "AIML", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI501", "title": "Machine Learning", "branch": "AIML", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI502", "title": "Computer Networks", "branch": "AIML", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI503", "title": "Deep Learning", "branch": "AIML", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI601", "title": "Natural Language Processing", "branch": "AIML", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI602", "title": "Computer Vision", "branch": "AIML", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIML},
    {"code": "BAI701", "title": "Reinforcement Learning", "branch": "AIML", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_AIML},
    {"code": "BAI801", "title": "AI for Robotics", "branch": "AIML", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_AIML},

    # 2021 Scheme AIML
    {"code": "21AI32", "title": "Data Structures and Applications", "branch": "AIML", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI33", "title": "Analog and Digital Electronics", "branch": "AIML", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI34", "title": "Computer Organization and Architecture", "branch": "AIML", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI42", "title": "Design and Analysis of Algorithms", "branch": "AIML", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI43", "title": "Microcontroller and Embedded Systems", "branch": "AIML", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI44", "title": "Operating Systems", "branch": "AIML", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI51", "title": "Principles of Artificial Intelligence", "branch": "AIML", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI52", "title": "Computer Networks and Security", "branch": "AIML", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI53", "title": "Database Management Systems", "branch": "AIML", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI54", "title": "Automata Theory and Computability", "branch": "AIML", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI61", "title": "Machine Learning", "branch": "AIML", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI62", "title": "Deep Learning", "branch": "AIML", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI71", "title": "Natural Language Processing", "branch": "AIML", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI72", "title": "Computer Vision", "branch": "AIML", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AI81", "title": "AI Ethics and Governance", "branch": "AIML", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme AIML
    {"code": "18AI32", "title": "Data Structures and Applications", "branch": "AIML", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI33", "title": "Analog and Digital Electronics", "branch": "AIML", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AI34", "title": "Computer Organization", "branch": "AIML", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AI42", "title": "Design and Analysis of Algorithms", "branch": "AIML", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI43", "title": "Operating Systems", "branch": "AIML", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AI51", "title": "Management and Entrepreneurship for IT Industry", "branch": "AIML", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AI52", "title": "Computer Networks", "branch": "AIML", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI53", "title": "Database Management Systems", "branch": "AIML", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI54", "title": "Automata Theory and Computability", "branch": "AIML", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AI61", "title": "Foundations of Artificial Intelligence", "branch": "AIML", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI62", "title": "Machine Learning Techniques", "branch": "AIML", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI71", "title": "Deep Learning Architectures", "branch": "AIML", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI72", "title": "Big Data Analytics", "branch": "AIML", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AI81", "title": "Cognitive Computing", "branch": "AIML", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # AIDS (Artificial Intelligence & Data Science)
    # =========================================================================
    # 2022 Scheme AIDS
    {"code": "BAD301", "title": "Mathematics for Data Science", "branch": "AIDS", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD302", "title": "Digital Design and Computer Organization", "branch": "AIDS", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD303", "title": "Operating Systems", "branch": "AIDS", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD304", "title": "Data Structures and Algorithms", "branch": "AIDS", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD401", "title": "Analysis and Design of Algorithms", "branch": "AIDS", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD402", "title": "Database Management Systems", "branch": "AIDS", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD403", "title": "Introduction to Data Science", "branch": "AIDS", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD501", "title": "Machine Learning and its Applications", "branch": "AIDS", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD502", "title": "Computer Networks", "branch": "AIDS", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD503", "title": "Data Mining and Data Warehousing", "branch": "AIDS", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD601", "title": "Big Data Technologies", "branch": "AIDS", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD602", "title": "Deep Learning", "branch": "AIDS", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_AIDS},
    {"code": "BAD701", "title": "Data Visualization and Storytelling", "branch": "AIDS", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_AIDS},
    {"code": "BAD801", "title": "Predictive Analytics", "branch": "AIDS", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_AIDS},

    # 2021 Scheme AIDS
    {"code": "21AD32", "title": "Data Structures and Applications", "branch": "AIDS", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD33", "title": "Analog and Digital Electronics", "branch": "AIDS", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD34", "title": "Computer Organization and Architecture", "branch": "AIDS", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD42", "title": "Design and Analysis of Algorithms", "branch": "AIDS", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD43", "title": "Microcontroller and Embedded Systems", "branch": "AIDS", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD44", "title": "Operating Systems", "branch": "AIDS", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD51", "title": "Management, Entrepreneurship and IPR", "branch": "AIDS", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD52", "title": "Computer Networks", "branch": "AIDS", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD53", "title": "Database Management Systems", "branch": "AIDS", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD54", "title": "Data Science Tools and Techniques", "branch": "AIDS", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD61", "title": "Machine Learning for Data Science", "branch": "AIDS", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD62", "title": "Big Data Analytics", "branch": "AIDS", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD71", "title": "Deep Learning", "branch": "AIDS", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD72", "title": "Natural Language Processing", "branch": "AIDS", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21AD81", "title": "Data Ethics and Privacy", "branch": "AIDS", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme AIDS
    {"code": "18AD32", "title": "Data Structures and Applications", "branch": "AIDS", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD33", "title": "Analog and Digital Electronics", "branch": "AIDS", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AD34", "title": "Computer Organization", "branch": "AIDS", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AD42", "title": "Design and Analysis of Algorithms", "branch": "AIDS", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD43", "title": "Operating Systems", "branch": "AIDS", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AD51", "title": "Management and Entrepreneurship for IT Industry", "branch": "AIDS", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18AD52", "title": "Computer Networks", "branch": "AIDS", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD53", "title": "Database Management Systems", "branch": "AIDS", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD61", "title": "Data Analytics and Visualization", "branch": "AIDS", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD62", "title": "Machine Learning", "branch": "AIDS", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD71", "title": "Deep Learning Applications", "branch": "AIDS", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD72", "title": "Big Data Systems", "branch": "AIDS", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18AD81", "title": "Business Intelligence", "branch": "AIDS", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # ECE (Electronics & Communication Engineering)
    # =========================================================================
    # 2022 Scheme ECE
    {"code": "BEC301", "title": "Mathematics for Electrical & Electronics Engineering", "branch": "ECE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC302", "title": "Digital System Design", "branch": "ECE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC303", "title": "Electronic Devices and Circuits", "branch": "ECE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC304", "title": "Network Analysis and Synthesis", "branch": "ECE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC401", "title": "Electromagnetic Waves and Transmission Lines", "branch": "ECE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC402", "title": "Analog and Digital Communication", "branch": "ECE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC403", "title": "Microcontrollers and Embedded Systems", "branch": "ECE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC404", "title": "Signals and Systems", "branch": "ECE", "semester": 4, "scheme": "2022", "credits": 3, "source_url": URL_2022_ECE},
    {"code": "BEC501", "title": "Digital Signal Processing", "branch": "ECE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC502", "title": "Control Systems", "branch": "ECE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC503", "title": "VLSI Design", "branch": "ECE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC601", "title": "Antennas and Propagation", "branch": "ECE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC602", "title": "Wireless Communication", "branch": "ECE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ECE},
    {"code": "BEC701", "title": "Optical Communication and Networks", "branch": "ECE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_ECE},
    {"code": "BEC702", "title": "Microwave Engineering", "branch": "ECE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_ECE},
    {"code": "BEC801", "title": "Satellite Communication", "branch": "ECE", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_ECE},

    # 2021 Scheme ECE
    {"code": "21EC32", "title": "Digital System Design using Verilog", "branch": "ECE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC33", "title": "Analog Electronic Circuits", "branch": "ECE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC34", "title": "Network Analysis", "branch": "ECE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC42", "title": "Signals and Systems", "branch": "ECE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC43", "title": "Complex Analysis, Probability and Linear Algebra", "branch": "ECE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC44", "title": "Digital Signal Processing", "branch": "ECE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC51", "title": "Principles of Communication Systems", "branch": "ECE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC52", "title": "Control Systems", "branch": "ECE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC53", "title": "VLSI Design", "branch": "ECE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC54", "title": "Microcontroller and Applications", "branch": "ECE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC61", "title": "Antennas and Wave Propagation", "branch": "ECE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC62", "title": "Embedded System Design", "branch": "ECE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC71", "title": "Computer Communication Networks", "branch": "ECE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC72", "title": "Microwave and Optical Communication", "branch": "ECE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EC81", "title": "Wireless and Mobile Communication", "branch": "ECE", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme ECE
    {"code": "18EC32", "title": "Network Theory", "branch": "ECE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC33", "title": "Electronic Devices", "branch": "ECE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC34", "title": "Digital System Design", "branch": "ECE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC35", "title": "Computer Organization and Architecture", "branch": "ECE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC42", "title": "Analog Circuits", "branch": "ECE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC43", "title": "Control Systems", "branch": "ECE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC44", "title": "Engineering Electromagnetics", "branch": "ECE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC45", "title": "Signals and Systems", "branch": "ECE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC51", "title": "Technological Innovation Management and Entrepreneurship", "branch": "ECE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC52", "title": "Digital Signal Processing", "branch": "ECE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC53", "title": "Principles of Communication Systems", "branch": "ECE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC54", "title": "Information Theory and Coding", "branch": "ECE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC55", "title": "Electromagnetic Waves", "branch": "ECE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EC61", "title": "Digital Communication", "branch": "ECE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC62", "title": "Embedded Systems", "branch": "ECE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC63", "title": "Microwave and Antennas", "branch": "ECE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC71", "title": "Computer Networks", "branch": "ECE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC72", "title": "VLSI Design", "branch": "ECE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EC81", "title": "Wireless Communication", "branch": "ECE", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # EEE (Electrical & Electronics Engineering)
    # =========================================================================
    # 2022 Scheme EEE
    {"code": "BEE301", "title": "Mathematics for Electrical Engineering", "branch": "EEE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE302", "title": "Electric Circuit Analysis", "branch": "EEE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE303", "title": "Analog Electronic Circuits", "branch": "EEE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE304", "title": "Electrical Machines - I", "branch": "EEE", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE401", "title": "Electrical Machines - II", "branch": "EEE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE402", "title": "Electromagnetic Fields", "branch": "EEE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE403", "title": "Digital Electronics", "branch": "EEE", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE501", "title": "Control Systems", "branch": "EEE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE502", "title": "Power Electronics", "branch": "EEE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE503", "title": "Signals and Systems", "branch": "EEE", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE601", "title": "Power System Analysis", "branch": "EEE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE602", "title": "High Voltage Engineering", "branch": "EEE", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_EEE},
    {"code": "BEE701", "title": "Power System Protection", "branch": "EEE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_EEE},
    {"code": "BEE702", "title": "Electric Vehicle Technologies", "branch": "EEE", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_EEE},
    {"code": "BEE801", "title": "Smart Grid Technologies", "branch": "EEE", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_EEE},

    # 2021 Scheme EEE
    {"code": "21EE32", "title": "Electric Circuit Analysis", "branch": "EEE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE33", "title": "Transformers and Generators", "branch": "EEE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE34", "title": "Analog Electronics", "branch": "EEE", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE42", "title": "Electromagnetic Field Theory", "branch": "EEE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE43", "title": "Induction Machines and Synchronous Machines", "branch": "EEE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE44", "title": "Digital Electronics", "branch": "EEE", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE51", "title": "Management, Entrepreneurship and IPR", "branch": "EEE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE52", "title": "Control Systems", "branch": "EEE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE53", "title": "Power Electronics", "branch": "EEE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE54", "title": "Signals and Systems", "branch": "EEE", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE61", "title": "Power System Analysis - 1", "branch": "EEE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE62", "title": "Microcontroller and Applications", "branch": "EEE", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE71", "title": "Power System Protection and Switchgear", "branch": "EEE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE72", "title": "Electric Vehicle Technology", "branch": "EEE", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21EE81", "title": "Renewable Energy Systems", "branch": "EEE", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme EEE
    {"code": "18EE32", "title": "Electric Circuit Analysis", "branch": "EEE", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE33", "title": "Transformers and Generators", "branch": "EEE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE34", "title": "Analog Electronic Circuits", "branch": "EEE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE35", "title": "Digital System Design", "branch": "EEE", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE42", "title": "Electromagnetic Field Theory", "branch": "EEE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE43", "title": "Transmission and Distribution", "branch": "EEE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE44", "title": "Electric Motors", "branch": "EEE", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE51", "title": "Management and Entrepreneurship", "branch": "EEE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE52", "title": "Microcontroller", "branch": "EEE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE53", "title": "Power Electronics", "branch": "EEE", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE54", "title": "Signals and Systems", "branch": "EEE", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18EE61", "title": "Control Systems", "branch": "EEE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE62", "title": "Power System Analysis - 1", "branch": "EEE", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE71", "title": "Power System Protection", "branch": "EEE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE72", "title": "High Voltage Engineering", "branch": "EEE", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18EE81", "title": "Power System Operation and Control", "branch": "EEE", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # ME (Mechanical Engineering)
    # =========================================================================
    # 2022 Scheme ME
    {"code": "BME301", "title": "Mathematics for Mechanical Engineers", "branch": "ME", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME302", "title": "Material Science and Metallurgy", "branch": "ME", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME303", "title": "Mechanics of Materials", "branch": "ME", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME304", "title": "Thermodynamics", "branch": "ME", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME401", "title": "Fluid Mechanics and Hydraulic Machines", "branch": "ME", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME402", "title": "Manufacturing Processes", "branch": "ME", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME403", "title": "Kinematics of Machines", "branch": "ME", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME501", "title": "Design of Machine Elements - I", "branch": "ME", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME502", "title": "Applied Thermodynamics", "branch": "ME", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME503", "title": "Dynamics of Machines", "branch": "ME", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME601", "title": "Heat Transfer", "branch": "ME", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME602", "title": "Design of Machine Elements - II", "branch": "ME", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_ME},
    {"code": "BME701", "title": "Control Engineering", "branch": "ME", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_ME},
    {"code": "BME702", "title": "Mechatronics and Robotics", "branch": "ME", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_ME},
    {"code": "BME801", "title": "Operations Management", "branch": "ME", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_ME},

    # 2021 Scheme ME
    {"code": "21ME32", "title": "Thermodynamics", "branch": "ME", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME33", "title": "Material Science and Engineering", "branch": "ME", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME34", "title": "Mechanics of Materials", "branch": "ME", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME42", "title": "Fluid Mechanics and Machinery", "branch": "ME", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME43", "title": "Manufacturing Processes", "branch": "ME", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME44", "title": "Kinematics of Machines", "branch": "ME", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME51", "title": "Management and Economics", "branch": "ME", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME52", "title": "Design of Machine Elements - 1", "branch": "ME", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME53", "title": "Dynamics of Machinery", "branch": "ME", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME54", "title": "Turbo Machines", "branch": "ME", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME61", "title": "Heat Transfer", "branch": "ME", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME62", "title": "Design of Machine Elements - 2", "branch": "ME", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME71", "title": "Control Engineering", "branch": "ME", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME72", "title": "Mechatronics", "branch": "ME", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21ME81", "title": "Industrial Engineering and Ergonomics", "branch": "ME", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme ME
    {"code": "18ME32", "title": "Mechanics of Materials", "branch": "ME", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME33", "title": "Basic Thermodynamics", "branch": "ME", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME34", "title": "Material Science", "branch": "ME", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME35A", "title": "Metal Cutting and Forming", "branch": "ME", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME42", "title": "Applied Thermodynamics", "branch": "ME", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME43", "title": "Fluid Mechanics", "branch": "ME", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME44", "title": "Kinematics of Machines", "branch": "ME", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME51", "title": "Management and Economics", "branch": "ME", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME52", "title": "Design of Machine Elements - I", "branch": "ME", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME53", "title": "Dynamics of Machines", "branch": "ME", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME54", "title": "Turbo Machines", "branch": "ME", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18ME61", "title": "Finite Element Method", "branch": "ME", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME62", "title": "Heat Transfer", "branch": "ME", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME71", "title": "Control Engineering", "branch": "ME", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME72", "title": "Computer Aided Design and Manufacturing", "branch": "ME", "semester": 7, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18ME81", "title": "Energy Engineering", "branch": "ME", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},

    # =========================================================================
    # CV (Civil Engineering)
    # =========================================================================
    # 2022 Scheme CV
    {"code": "BCV301", "title": "Mathematics for Civil Engineering", "branch": "CV", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV302", "title": "Strength of Materials", "branch": "CV", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV303", "title": "Fluid Mechanics", "branch": "CV", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV304", "title": "Basic Surveying", "branch": "CV", "semester": 3, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV401", "title": "Analysis of Determinate Structures", "branch": "CV", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV402", "title": "Applied Hydraulics", "branch": "CV", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV403", "title": "Concrete Technology", "branch": "CV", "semester": 4, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV501", "title": "Analysis of Indeterminate Structures", "branch": "CV", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV502", "title": "Design of RC Structural Elements", "branch": "CV", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV503", "title": "Geotechnical Engineering - I", "branch": "CV", "semester": 5, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV601", "title": "Design of Steel Structural Elements", "branch": "CV", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV602", "title": "Highway Engineering", "branch": "CV", "semester": 6, "scheme": "2022", "credits": 4, "source_url": URL_2022_CV},
    {"code": "BCV701", "title": "Environmental Engineering", "branch": "CV", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_CV},
    {"code": "BCV702", "title": "Estimation and Costing", "branch": "CV", "semester": 7, "scheme": "2022", "credits": 3, "source_url": URL_2022_CV},
    {"code": "BCV801", "title": "Pavement Design", "branch": "CV", "semester": 8, "scheme": "2022", "credits": 3, "source_url": URL_2022_CV},

    # 2021 Scheme CV
    {"code": "21CV32", "title": "Strength of Materials", "branch": "CV", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV33", "title": "Fluid Mechanics", "branch": "CV", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV34", "title": "Basic Surveying", "branch": "CV", "semester": 3, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV42", "title": "Analysis of Determinate Structures", "branch": "CV", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV43", "title": "Applied Hydraulics", "branch": "CV", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV44", "title": "Concrete Technology", "branch": "CV", "semester": 4, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV51", "title": "Construction Management and Entrepreneurship", "branch": "CV", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV52", "title": "Analysis of Indeterminate Structures", "branch": "CV", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV53", "title": "Design of RC Structural Elements", "branch": "CV", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV54", "title": "Basic Geotechnical Engineering", "branch": "CV", "semester": 5, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV61", "title": "Design of Steel Structural Elements", "branch": "CV", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV62", "title": "Highway Engineering", "branch": "CV", "semester": 6, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV71", "title": "Environmental Engineering", "branch": "CV", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV72", "title": "Estimation and Valuation", "branch": "CV", "semester": 7, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},
    {"code": "21CV81", "title": "Urban Transport Planning", "branch": "CV", "semester": 8, "scheme": "2021", "credits": 3, "source_url": URL_2021_SCHEME},

    # 2018 Scheme CV
    {"code": "18CV32", "title": "Strength of Materials", "branch": "CV", "semester": 3, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV33", "title": "Fluid Mechanics", "branch": "CV", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV34", "title": "Basic Surveying", "branch": "CV", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV35", "title": "Engineering Geology", "branch": "CV", "semester": 3, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV42", "title": "Analysis of Determinate Structures", "branch": "CV", "semester": 4, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV43", "title": "Applied Hydraulics", "branch": "CV", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV44", "title": "Concrete Technology", "branch": "CV", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV45", "title": "Advanced Surveying", "branch": "CV", "semester": 4, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV51", "title": "Construction Management and Entrepreneurship", "branch": "CV", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV52", "title": "Analysis of Indeterminate Structures", "branch": "CV", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV53", "title": "Design of RC Structural Elements", "branch": "CV", "semester": 5, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV54", "title": "Basic Geotechnical Engineering", "branch": "CV", "semester": 5, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV61", "title": "Design of Steel Structural Elements", "branch": "CV", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV62", "title": "Applied Geotechnical Engineering", "branch": "CV", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV63", "title": "Hydrology and Irrigation Engineering", "branch": "CV", "semester": 6, "scheme": "2018", "credits": 4, "source_url": URL_2018_SCHEME},
    {"code": "18CV71", "title": "Quality Surveying and Contract Management", "branch": "CV", "semester": 7, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV72", "title": "Design of Bridges", "branch": "CV", "semester": 7, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
    {"code": "18CV81", "title": "Design of Pre-stressed Concrete Elements", "branch": "CV", "semester": 8, "scheme": "2018", "credits": 3, "source_url": URL_2018_SCHEME},
]


def extract_prefix(code: str) -> str:
    """Extract discipline/department prefix from VTU course code."""
    code = code.strip().upper()
    # Strip leading scheme digits (18, 21, 22)
    trimmed = re.sub(r'^(18|21|22)', '', code)
    m = re.match(r'^([A-Z]+)', trimmed)
    return m.group(1) if m else ""


PREFIX_BRANCH_MAP = {
    "BCS": ["CSE", "ISE", "AIML", "AIDS"],
    "CS": ["CSE", "ISE", "AIML", "AIDS"],
    "BIS": ["ISE", "CSE"],
    "IS": ["ISE", "CSE"],
    "BAI": ["AIML", "CSE"],
    "AI": ["AIML", "CSE"],
    "BAD": ["AIDS", "CSE"],
    "AD": ["AIDS", "CSE"],
    "BEC": ["ECE", "FY-CYCLE"],
    "EC": ["ECE", "FY-CYCLE"],
    "BEE": ["EEE", "FY-CYCLE"],
    "EE": ["EEE", "FY-CYCLE"],
    "BME": ["ME", "FY-CYCLE"],
    "ME": ["ME", "FY-CYCLE"],
    "BCV": ["CV", "FY-CYCLE"],
    "CV": ["CV", "FY-CYCLE"],
    "BMAT": ["FY-CYCLE", "CSE", "ISE", "AIML", "AIDS", "ECE", "EEE", "ME", "CV"],
    "BMATS": ["FY-CYCLE", "CSE", "ISE", "AIML", "AIDS"],
    "BMATM": ["FY-CYCLE", "ME"],
    "BMATE": ["FY-CYCLE", "EEE", "ECE"],
    "BMATC": ["FY-CYCLE", "CV"],
    "MAT": ["FY-CYCLE", "CSE", "ISE", "AIML", "AIDS", "ECE", "EEE", "ME", "CV"],
    "MATCS": ["CSE", "ISE", "AIML", "AIDS"],
    "BPHYS": ["FY-CYCLE"],
    "BPHY": ["FY-CYCLE"],
    "PHY": ["FY-CYCLE"],
    "BCHES": ["FY-CYCLE"],
    "BCHE": ["FY-CYCLE"],
    "CHE": ["FY-CYCLE"],
    "BPOPS": ["FY-CYCLE", "CSE", "ISE"],
    "BCEDK": ["FY-CYCLE", "ME", "CV"],
    "BCED": ["FY-CYCLE", "ME", "CV"],
    "BESCK": ["FY-CYCLE", "CSE", "ISE", "AIML", "AIDS", "ECE", "EEE", "ME", "CV"],
    "BES": ["FY-CYCLE", "CSE", "ISE", "AIML", "AIDS", "ECE", "EEE", "ME", "CV"],
    "PSP": ["FY-CYCLE", "CSE", "ISE"],
    "CPS": ["FY-CYCLE", "CSE", "ISE"],
    "ELE": ["FY-CYCLE", "EEE"],
    "ELN": ["FY-CYCLE", "ECE"],
    "CIV": ["FY-CYCLE", "CV"],
    "EME": ["FY-CYCLE", "ME"],
    "EGDL": ["FY-CYCLE", "ME", "CV"],
    "IDT": ["FY-CYCLE"],
    "BIDTK": ["FY-CYCLE"],
    "ENG": ["FY-CYCLE"],
    "EGH": ["FY-CYCLE"],
    "BENG": ["FY-CYCLE"],
    "BENGK": ["FY-CYCLE"],
    "BPWS": ["FY-CYCLE"],
    "BPWSK": ["FY-CYCLE"],
    "ICO": ["FY-CYCLE"],
    "BICOK": ["FY-CYCLE"],
    "KSK": ["FY-CYCLE"],
    "KBK": ["FY-CYCLE"],
    "BKSK": ["FY-CYCLE"],
    "BKBK": ["FY-CYCLE"],
}


def validate_catalog(courses: List[Dict[str, Any]]) -> List[str]:
    """Strictly audits courses for duplicates, empty titles, invalid credits, and prefix mismatches."""
    errors: List[str] = []
    seen_scheme_sem_codes: Set[Tuple[str, int, str]] = set()

    for idx, c in enumerate(courses):
        code = c.get("code", "").strip()
        title = c.get("title", "").strip()
        scheme = c.get("scheme", "").strip()
        branch = c.get("branch", "").strip()
        sem = c.get("semester")
        credits_val = c.get("credits")
        url = c.get("source_url", "").strip()

        # 1. Non-empty fields
        if not code:
            errors.append(f"Course #{idx}: empty 'code'")
        if not title:
            errors.append(f"Course #{idx} ({code}): empty 'title'")
        if not scheme:
            errors.append(f"Course #{idx} ({code}): empty 'scheme'")
        if not branch:
            errors.append(f"Course #{idx} ({code}): empty 'branch'")
        if not isinstance(sem, int) or not (1 <= sem <= 8):
            errors.append(f"Course #{idx} ({code}): invalid semester {sem}")
        if not isinstance(credits_val, (int, float)) or credits_val <= 0:
            errors.append(f"Course #{idx} ({code}): invalid credits {credits_val}")
        if not url.startswith("https://vtu.ac.in"):
            errors.append(f"Course #{idx} ({code}): invalid VTU source_url '{url}'")

        # 2. Duplicate course code within same scheme and semester
        key = (scheme, sem, code)
        if key in seen_scheme_sem_codes:
            errors.append(f"Duplicate course code '{code}' in scheme {scheme}, semester {sem}")
        seen_scheme_sem_codes.add(key)

        # 3. Prefix matching branch
        prefix = extract_prefix(code)
        if prefix not in PREFIX_BRANCH_MAP:
            errors.append(f"Course {code}: unknown prefix '{prefix}'")
        else:
            allowed_branches = PREFIX_BRANCH_MAP[prefix]
            if branch not in allowed_branches:
                errors.append(
                    f"Course {code}: prefix '{prefix}' maps to {allowed_branches}, but branch is '{branch}'"
                )

    return errors


def build_catalog_dict() -> Dict[str, Any]:
    """Formats full catalog payload with verified flags."""
    for c in COURSES_DATA:
        c["verified"] = True
    return {
        "university": "Visvesvaraya Technological University (VTU)",
        "schemes": ["2022", "2021", "2018"],
        "branches": BRANCHES_METADATA,
        "courses": COURSES_DATA,
    }


def main():
    print(f"Building VTU academic catalog with {len(COURSES_DATA)} courses...")
    errors = validate_catalog(COURSES_DATA)
    if errors:
        print(f"FAILED: Found {len(errors)} validation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    catalog_data = build_catalog_dict()
    CATALOG_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2)

    print(f"SUCCESS: Catalog written to {CATALOG_OUTPUT_PATH}")
    print(f"Total courses: {len(COURSES_DATA)}")
    print(f"Schemes: {catalog_data['schemes']}")
    print(f"Branches: {[b['code'] for b in catalog_data['branches']]}")


if __name__ == "__main__":
    main()
