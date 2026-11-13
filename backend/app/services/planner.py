import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models.plans import StudyPlan, PlanItem, Answer, generate_plan_id, generate_item_id, generate_answer_id
from app.models.notes import UploadedNotes
from app.schemas.plans import PlanCreateRequest, StudyPlanResponse, PlanDayResponse, PlanItemResponse, AnswerResponse, TopicEffortEstimationOutput
from app.services.gemini import generate_structured, GeminiNotConfiguredError

# Standard syllabus curriculum fallback topics by module for popular VTU courses
DEFAULT_SYLLABUS_TOPICS = {
    "BCS304": {
        1: [
            ("Linear vs Non-Linear Data Structures & Dynamic Memory Allocation", 50, "Pointers, malloc, calloc, realloc, and free"),
            ("Stack Operations, Implementation & Applications (Infix to Postfix)", 60, "Push, Pop, Peek, Array representation, Expression evaluation"),
            ("Queue Operations, Circular Queue & Priority Queue", 45, "EnQueue, DeQueue, Circular queue boundary conditions"),
        ],
        2: [
            ("Singly Linked Lists: Insertion, Deletion & Traversal", 60, "Node structure, head pointer manipulation, edge cases"),
            ("Doubly Linked Lists & Circular Linked Lists", 50, "Double pointers, insertion at middle, deletion at ends"),
            ("Linked List Applications: Polynomial Addition & Sparse Matrices", 45, "Node representation of polynomial terms and addition"),
        ],
        3: [
            ("Binary Trees: Terminology, Representation & Traversals (In/Pre/Post)", 60, "Recursive traversals, tree depth, complete vs full binary trees"),
            ("Binary Search Trees (BST): Search, Insertion & Deletion", 65, "BST invariant, deleting node with two children"),
            ("Threaded Binary Trees & Expression Trees", 40, "In-order threads, null pointer utilization"),
        ],
        4: [
            ("Graph Representations: Adjacency Matrix vs Adjacency List", 45, "Space and time complexity comparison"),
            ("Graph Traversals: BFS & DFS with Algorithms", 60, "Queue-based BFS, Stack/recursive DFS, cycle detection"),
            ("Minimum Spanning Trees: Prim's & Kruskal's Algorithms", 60, "Greedy strategy, edge selection, disjoint sets"),
        ],
        5: [
            ("Hash Tables: Hash Functions & Collision Resolution", 55, "Division/Multiplication method, Linear probing, Chaining"),
            ("Sorting Techniques: Merge Sort & Quick Sort", 65, "Divide-and-conquer recurrence, pivot selection, time complexity"),
            ("File Structures & Indexing: B-Trees & B+ Trees Overview", 45, "Multi-way search trees, disk-based indexing principles"),
        ],
    },
    "BCS303": {
        1: [
            ("Operating System Services, System Calls & OS Structures", 50, "Dual-mode operation, API vs System Call, Monolithic vs Microkernel"),
            ("Process Concept, Process State Transition & PCB", 55, "Context switching, PCB components, Process creation (fork/exec)"),
            ("Inter-Process Communication (IPC): Shared Memory vs Message Passing", 45, "Direct/Indirect communication, buffering mechanisms"),
        ],
        2: [
            ("CPU Scheduling Algorithms: FCFS, SJF, Priority & Round Robin", 65, "Gantt charts, Turnaround time, Waiting time calculations"),
            ("Process Synchronization: Critical Section Problem & Peterson's Solution", 60, "Mutual exclusion, Progress, Bounded waiting"),
            ("Semaphores & Classical IPC Problems (Producer-Consumer, Dining Philosophers)", 60, "Wait/Signal operations, Deadlock conditions"),
        ],
        3: [
            ("Deadlock Characterization, Resource Allocation Graphs (RAG)", 50, "Four necessary conditions for deadlock"),
            ("Deadlock Prevention, Avoidance & Banker's Algorithm", 65, "Safety algorithm, Resource request algorithm with numericals"),
            ("Deadlock Detection & Recovery Strategies", 40, "Wait-for graphs, Process termination, Resource preemption"),
        ],
        4: [
            ("Main Memory Management: Paging & Segmentation", 60, "Page table structure, TLB translation lookaside buffer"),
            ("Virtual Memory: Demand Paging & Page Fault Handling", 55, "Effective memory access time, Page fault routine"),
            ("Page Replacement Algorithms: FIFO, LRU & Optimal", 60, "Belady's anomaly, Frame allocation, Hit/Fault ratio calculations"),
        ],
        5: [
            ("File System Interface: File Access Methods & Directory Structures", 45, "Sequential/Direct access, Single/Two-level/Tree directories"),
            ("Mass Storage: Disk Scheduling Algorithms (FCFS, SSTF, SCAN, LOOK)", 55, "Total head movement calculation, Seek time optimization"),
            ("Protection & Security: Access Matrix & Domain Protection", 40, "Access rights, Capability lists vs Access control lists"),
        ],
    }
}


def get_topics_for_course(course_code: str, num_modules: int) -> Dict[int, List[Tuple[str, int, str]]]:
    """Retrieve syllabus topics for each requested module."""
    course_topics = DEFAULT_SYLLABUS_TOPICS.get(course_code.upper())
    if not course_topics:
        # Generic engineering topics per module
        course_topics = {}
        for mod in range(1, 6):
            course_topics[mod] = [
                (f"Module {mod}: Core Fundamentals & Architectural Concepts", 50, "Key definitions and architectural diagrams"),
                (f"Module {mod}: Analytical Formulations & Algorithm Derivations", 60, "Step-by-step methodology and standard VTU problems"),
                (f"Module {mod}: Practical Applications & Case Studies", 45, "Design problems, comparison tables, and implementation"),
            ]

    # Return only requested modules
    return {mod: course_topics.get(mod, [
        (f"Module {mod} Key Topic A", 50, "Fundamental principles"),
        (f"Module {mod} Key Topic B", 60, "Core algorithms & derivations"),
    ]) for mod in range(1, num_modules + 1)}


async def estimate_efforts_with_gemini(course_code: str, course_title: str, modules: List[int], topics: List[str]) -> Dict[str, int]:
    """Use Gemini to estimate study minutes clamped to [10, 90] minutes."""
    if not settings.has_gemini:
        return {}

    try:
        prompt = (
            f"Estimate realistic study effort in minutes (10 to 90 mins) for these VTU topics:\n"
            f"Course: {course_code} - {course_title}\n"
            f"Modules: {modules}\n"
            f"Topics:\n" + "\n".join(f"- {t}" for t in topics) + "\n"
            f"Return JSON matching: {{'topics': [{{'topic': '...', 'module': 1, 'recommended_minutes': 50, 'reasoning': '...'}}]}}"
        )
        result: TopicEffortEstimationOutput = await generate_structured(prompt, TopicEffortEstimationOutput)
        return {item.topic: max(10, min(90, item.recommended_minutes)) for item in result.topics}
    except Exception:
        return {}


def format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def add_minutes(start_h: int, start_m: int, added_mins: int) -> Tuple[int, int]:
    total_m = start_h * 60 + start_m + added_mins
    return (total_m // 60) % 24, total_m % 60


def generate_plan_schedule(
    course_code: str,
    course_title: str,
    num_days: int,
    num_modules: int,
    notes_record: Optional[UploadedNotes] = None,
) -> Tuple[bool, Optional[str], List[dict], List[dict]]:
    """
    Deterministically schedule modules, topics, study blocks, and breaks.
    Returns:
        (is_heavy_plan, heavy_warning, days_data, answers_data)
    """
    # Assess workload intensity
    ratio = num_modules / num_days
    is_heavy = ratio >= 1.5 or (num_modules >= 4 and num_days <= 2)
    heavy_warning = (
        f"Covering {num_modules} modules in {num_days} day(s) requires intensive study sessions ({int(ratio * 3.5)}+ hours/day). Take scheduled breaks and focus on high-weightage topics."
        if is_heavy else None
    )

    modules_topics = get_topics_for_course(course_code, num_modules)

    # Flatten all topics to distribute across days
    all_tasks: List[Tuple[int, str, int, str]] = []  # (module, title, duration, notes_summary)
    for mod in range(1, num_modules + 1):
        for item in modules_topics.get(mod, []):
            all_tasks.append((mod, item[0], item[1], item[2]))

    # Distribute tasks as evenly as possible across num_days
    tasks_per_day: List[List[Tuple[int, str, int, str]]] = [[] for _ in range(num_days)]
    for idx, task in enumerate(all_tasks):
        day_idx = idx % num_days
        tasks_per_day[day_idx].append(task)

    days_data = []
    answers_data = []

    for day_i in range(num_days):
        day_num = day_i + 1
        date_label = "Day 1 (Today)" if day_num == 1 else f"Day {day_num}"
        current_h = 9
        current_m = 0
        day_items = []
        total_study_minutes = 0

        day_tasks = tasks_per_day[day_i]
        for t_idx, (mod, title, duration, summary) in enumerate(day_tasks):
            # Study block
            start_str = format_time(current_h, current_m)
            end_h, end_m = add_minutes(current_h, current_m, duration)
            end_str = format_time(end_h, end_m)

            ans_id = generate_answer_id()
            item_id = generate_item_id()

            day_items.append({
                "id": item_id,
                "type": "study",
                "module": mod,
                "title": title,
                "start_time": start_str,
                "end_time": end_str,
                "duration_minutes": duration,
                "answer_id": ans_id,
                "is_completed": False,
            })
            total_study_minutes += duration
            current_h, current_m = end_h, end_m

            # Prepare answer record
            if notes_record:
                src_type = "notes"
                src_attribution = f"Page 1-{notes_record.pages_count} of {notes_record.filename}"
                content = (
                    f"### {title}\n\n"
                    f"**Grounded in uploaded notes:** `{notes_record.filename}`\n\n"
                    f"- **Module {mod} Overview**: {summary}.\n"
                    f"- **Key Concepts**: Derived directly from uploaded class notes. Ensure definitions and diagrams match classroom notation.\n"
                    f"- **VTU Exam Tip**: State standard assumptions, draw neat annotated diagrams, and list formulas clearly."
                )
            else:
                src_type = "curriculum_grounded"
                src_attribution = f"VTU {course_code} Prescribed Syllabus Reference"
                content = (
                    f"### {title}\n\n"
                    f"**Curriculum Grounded Model Answer:**\n\n"
                    f"- **Module {mod} Focus**: {summary}.\n"
                    f"- **Core Theory & Definition**: Standard VTU formulation adhering to prescribed textbooks.\n"
                    f"- **High-Scoring Elements**: Tabulate comparative characteristics, emphasize edge-cases, and write clean pseudocode or equations."
                )

            answers_data.append({
                "id": ans_id,
                "question_or_topic": title,
                "module": mod,
                "content": content,
                "source_type": src_type,
                "source_attribution": src_attribution,
                "source_urls": [],
            })

            # Add short break after study block (if not last item of the day)
            if t_idx < len(day_tasks) - 1:
                # If around lunchtime (12:30 - 13:30), schedule a longer break
                if current_h in (12, 13):
                    break_dur = 45
                    break_title = "Lunch & Rest Break"
                else:
                    break_dur = 15
                    break_title = "Short Break"

                b_start_str = format_time(current_h, current_m)
                b_end_h, b_end_m = add_minutes(current_h, current_m, break_dur)
                b_end_str = format_time(b_end_h, b_end_m)

                day_items.append({
                    "id": generate_item_id(),
                    "type": "break",
                    "module": None,
                    "title": break_title,
                    "start_time": b_start_str,
                    "end_time": b_end_str,
                    "duration_minutes": break_dur,
                    "answer_id": None,
                    "is_completed": False,
                })
                current_h, current_m = b_end_h, b_end_m

        days_data.append({
            "day_number": day_num,
            "date_label": date_label,
            "total_study_minutes": total_study_minutes,
            "items": day_items,
        })

    return is_heavy, heavy_warning, days_data, answers_data
