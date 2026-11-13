"""
Deterministic Timetable Scheduling Engine for VTU Study Planner.

Follows API contract in docs/CONTRACT.md and .agent/skills/study-scheduler/SKILL.md.
Zero external LLM dependencies - fully deterministic Python logic.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes from midnight."""
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to 'HH:MM' string."""
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def get_item_duration(item: Dict[str, Any]) -> int:
    """Extract duration in minutes from various possible keys."""
    for key in ("duration_minutes", "estimated_minutes", "effort_minutes", "duration"):
        if key in item and item[key] is not None:
            try:
                val = int(item[key])
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass
    return 60


def get_item_title(item: Dict[str, Any]) -> str:
    """Extract item title from various possible keys."""
    for key in ("title", "topic", "canonical_question", "question", "name"):
        if key in item and item[key]:
            return str(item[key]).strip()
    return "Core Study Topic"


def get_item_module(item: Dict[str, Any]) -> Optional[int]:
    """Extract module number from item dict."""
    mod = item.get("module")
    if mod is not None:
        try:
            return int(mod)
        except (ValueError, TypeError):
            pass
    return None


def split_into_sessions(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Split an item into contiguous study sessions of ~45 to 80 minutes.
    If duration <= 80 mins, keeps as a single session.
    If duration > 80 mins, splits into balanced parts of 45-80 mins each.
    """
    total_duration = get_item_duration(item)
    title = get_item_title(item)
    module = get_item_module(item)
    answer_id = item.get("answer_id") or item.get("id")
    description = item.get("description")

    if total_duration <= 80:
        return [
            {
                "title": title,
                "module": module,
                "duration_minutes": total_duration,
                "answer_id": answer_id,
                "description": description,
            }
        ]

    # Split into chunks of at most 75-80 mins
    num_parts = max(2, math.ceil(total_duration / 75.0))
    base_part = total_duration // num_parts
    remainder = total_duration % num_parts

    parts = []
    for p in range(num_parts):
        part_dur = base_part + (1 if p < remainder else 0)
        part_title = f"{title} (Part {p + 1}/{num_parts})"
        parts.append(
            {
                "title": part_title,
                "module": module,
                "duration_minutes": part_dur,
                "answer_id": answer_id,
                "description": description,
            }
        )
    return parts


def sort_items_by_module(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort items stably by module (Module 1, Module 2, ...) preserving internal order.
    Items without a module are placed with Module 1.
    """
    indexed = list(enumerate(items))

    def sort_key(entry):
        idx, itm = entry
        mod = get_item_module(itm)
        return (mod if mod is not None else 1, idx)

    indexed.sort(key=sort_key)
    return [itm for _, itm in indexed]


def partition_sessions_evenly(
    sessions: List[Dict[str, Any]], k_days: int
) -> List[List[Dict[str, Any]]]:
    """
    Partition contiguous sessions into k_days non-empty buckets
    using Dynamic Programming to minimize workload variance.
    Preserves contiguous order (and thus module contiguity).
    """
    n = len(sessions)
    if k_days <= 1:
        return [sessions]
    if n == 0:
        return [[] for _ in range(k_days)]
    if n <= k_days:
        result = [[sessions[i]] for i in range(n)]
        while len(result) < k_days:
            result.append([])
        return result

    durations = [s["duration_minutes"] for s in sessions]
    total_dur = sum(durations)
    target = total_dur / k_days

    # Prefix sums
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + durations[i]

    def cost(i: int, j: int) -> float:
        chunk_sum = prefix[j] - prefix[i]
        diff = chunk_sum - target
        return diff * diff

    # dp[k][i] = min cost to partition sessions[:i] into k non-empty chunks
    dp = [[float("inf")] * (n + 1) for _ in range(k_days + 1)]
    parent = [[0] * (n + 1) for _ in range(k_days + 1)]

    for i in range(1, n + 1):
        dp[1][i] = cost(0, i)
        parent[1][i] = 0

    for k in range(2, k_days + 1):
        for i in range(k, n + 1):
            for j in range(k - 1, i):
                c = dp[k - 1][j] + cost(j, i)
                if c < dp[k][i]:
                    dp[k][i] = c
                    parent[k][i] = j

    # Backtrack split points
    splits = [n]
    curr_k = k_days
    curr_i = n
    while curr_k > 1:
        prev_i = parent[curr_k][curr_i]
        splits.append(prev_i)
        curr_i = prev_i
        curr_k -= 1
    splits.reverse()

    chunks = []
    start = 0
    for end in splits:
        chunks.append(sessions[start:end])
        start = end

    return chunks


def schedule_study_day(
    day_num: int,
    sessions: List[Dict[str, Any]],
    is_single_day: bool,
    start_minutes: int = 540,  # 09:00
) -> List[Dict[str, Any]]:
    """
    Schedule a single study day's items:
    - Starts at 09:00
    - Study sessions ~45-80 mins
    - 15 min short breaks after sessions
    - 45 min lunch break around 13:00 (12:00 - 13:30 window)
    - 30 min end-of-day recap (if multi-day) OR 45 min afternoon revision (if single-day)
    - Perfectly continuous start/end times with zero overlap or gaps.
    """
    day_items: List[Dict[str, Any]] = []
    item_counter = 1
    current_time = start_minutes
    lunch_scheduled = False

    LUNCH_EARLIEST = 12 * 60  # 12:00
    LUNCH_TARGET = 13 * 60  # 13:00
    LUNCH_LATEST = 13 * 60 + 30  # 13:30
    LUNCH_DURATION = 45
    SHORT_BREAK_DURATION = 15
    RECAP_DURATION = 45 if is_single_day else 30

    # If day has no sessions, provide structured self-study block
    if not sessions:
        sessions = [
            {
                "title": "Module Core Concepts Self-Study & Practice",
                "module": 1,
                "duration_minutes": 75,
                "answer_id": None,
                "description": "Independent study and revision of syllabus topics.",
            }
        ]

    for i, session in enumerate(sessions):
        dur = session["duration_minutes"]

        # Check if lunch should be taken BEFORE this study session
        if not lunch_scheduled:
            if current_time >= LUNCH_TARGET:
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "lunch",
                        "module": None,
                        "title": "Lunch Break",
                        "description": "Midday meal and mental relaxation.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + LUNCH_DURATION),
                        "duration_minutes": LUNCH_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += LUNCH_DURATION
                lunch_scheduled = True
            elif current_time >= LUNCH_EARLIEST and (current_time + dur > LUNCH_LATEST):
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "lunch",
                        "module": None,
                        "title": "Lunch Break",
                        "description": "Midday meal and mental relaxation.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + LUNCH_DURATION),
                        "duration_minutes": LUNCH_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += LUNCH_DURATION
                lunch_scheduled = True

        # Study session
        day_items.append(
            {
                "id": f"item_d{day_num}_{item_counter:02d}",
                "day_number": day_num,
                "type": "study",
                "module": session.get("module"),
                "title": session["title"],
                "description": session.get("description"),
                "start_time": minutes_to_time(current_time),
                "end_time": minutes_to_time(current_time + dur),
                "duration_minutes": dur,
                "answer_id": session.get("answer_id"),
                "is_completed": False,
            }
        )
        item_counter += 1
        current_time += dur

        is_last_session = i == len(sessions) - 1

        if not is_last_session:
            next_dur = sessions[i + 1]["duration_minutes"]
            if not lunch_scheduled and (
                current_time >= LUNCH_TARGET
                or (current_time >= LUNCH_EARLIEST and current_time + next_dur > LUNCH_LATEST)
            ):
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "lunch",
                        "module": None,
                        "title": "Lunch Break",
                        "description": "Midday meal and mental relaxation.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + LUNCH_DURATION),
                        "duration_minutes": LUNCH_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += LUNCH_DURATION
                lunch_scheduled = True
            else:
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "break",
                        "module": None,
                        "title": "Short Break",
                        "description": "Quick rest and hydration.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + SHORT_BREAK_DURATION),
                        "duration_minutes": SHORT_BREAK_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += SHORT_BREAK_DURATION
        else:
            # Last study session on this day
            if not lunch_scheduled and current_time >= LUNCH_EARLIEST:
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "lunch",
                        "module": None,
                        "title": "Lunch Break",
                        "description": "Midday meal and mental relaxation.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + LUNCH_DURATION),
                        "duration_minutes": LUNCH_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += LUNCH_DURATION
                lunch_scheduled = True
            else:
                day_items.append(
                    {
                        "id": f"item_d{day_num}_{item_counter:02d}",
                        "day_number": day_num,
                        "type": "break",
                        "module": None,
                        "title": "Short Break",
                        "description": "Quick rest before recap.",
                        "start_time": minutes_to_time(current_time),
                        "end_time": minutes_to_time(current_time + SHORT_BREAK_DURATION),
                        "duration_minutes": SHORT_BREAK_DURATION,
                        "answer_id": None,
                        "is_completed": False,
                    }
                )
                item_counter += 1
                current_time += SHORT_BREAK_DURATION

            recap_title = (
                "Afternoon Comprehensive Revision & Practice"
                if is_single_day
                else f"Daily Recap & Formula Review (Day {day_num})"
            )
            day_items.append(
                {
                    "id": f"item_d{day_num}_{item_counter:02d}",
                    "day_number": day_num,
                    "type": "revision",
                    "module": None,
                    "title": recap_title,
                    "description": "Consolidate learning, review key formulas, and self-assess.",
                    "start_time": minutes_to_time(current_time),
                    "end_time": minutes_to_time(current_time + RECAP_DURATION),
                    "duration_minutes": RECAP_DURATION,
                    "answer_id": None,
                    "is_completed": False,
                }
            )
            item_counter += 1
            current_time += RECAP_DURATION

    return day_items


def schedule_final_revision_day(day_num: int, start_minutes: int = 540) -> List[Dict[str, Any]]:
    """
    Schedule final Day N dedicated to full syllabus revision & paper solving.
    Includes comprehensive revision sessions, model question paper solving, lunch at 13:00,
    short breaks, and final formula recall wrap-up.
    """
    day_items: List[Dict[str, Any]] = []
    item_counter = 1
    current_time = start_minutes

    blocks = [
        (
            "revision",
            "Full Syllabus Revision: High-Weightage Core Concepts (Part 1)",
            75,
            "Review foundational definitions, core concepts, and key theorems across all modules.",
        ),
        ("break", "Short Break", 15, "Hydrate and stretch."),
        (
            "revision",
            "Full Syllabus Revision: High-Weightage Core Concepts (Part 2)",
            75,
            "Deep-dive into repeated question topics, algorithms, and numerical problems.",
        ),
        ("break", "Short Break", 15, "Hydrate and rest eyes."),
        (
            "revision",
            "VTU Model Question Paper Solving (Session 1)",
            60,
            "Practice answering full model paper questions under exam conditions.",
        ),
        ("lunch", "Lunch Break", 45, "Midday meal and mental rest."),
        (
            "revision",
            "Previous Years Question Bank Practice (Session 2)",
            75,
            "High-frequency question patterns from recent VTU exams.",
        ),
        ("break", "Short Break", 15, "Short stretch and relaxation."),
        (
            "revision",
            "Final Formula, Diagrams & Quick Recall Wrap-Up",
            45,
            "Final rapid review of formulas, block diagrams, and exam presentation tips.",
        ),
    ]

    for b_type, b_title, b_dur, b_desc in blocks:
        day_items.append(
            {
                "id": f"item_d{day_num}_{item_counter:02d}",
                "day_number": day_num,
                "type": b_type,
                "module": None,
                "title": b_title,
                "description": b_desc,
                "start_time": minutes_to_time(current_time),
                "end_time": minutes_to_time(current_time + b_dur),
                "duration_minutes": b_dur,
                "answer_id": None,
                "is_completed": False,
            }
        )
        item_counter += 1
        current_time += b_dur

    return day_items


def generate_timetable(
    num_days: int,
    num_modules: int = 1,
    items_with_effort: Optional[List[Dict[str, Any]]] = None,
    course_code: str = "",
    course_title: str = "",
) -> Dict[str, Any]:
    """
    Generate a deterministic timetable adhering to VTU study guidelines.

    Parameters:
    - num_days: Total number of days for the plan (1 to 10).
    - num_modules: Total number of modules covered (at least 1).
    - items_with_effort: List of study items with estimated duration, module, title, etc.
    - course_code: VTU Course code (e.g., 'BCS304').
    - course_title: Course title (e.g., 'Data Structures and Applications').

    Returns cleanly structured dict compliant with docs/CONTRACT.md.
    """
    if not (1 <= num_days <= 10):
        raise ValueError("num_days must be between 1 and 10.")
    if num_modules < 1:
        raise ValueError("num_modules must be at least 1.")

    raw_items = items_with_effort if items_with_effort is not None else []

    # 1. Sort items stably by module to preserve contiguity
    sorted_items = sort_items_by_module(raw_items)

    # 2. Split each item into sessions of ~45-80 minutes
    all_sessions: List[Dict[str, Any]] = []
    for item in sorted_items:
        all_sessions.extend(split_into_sessions(item))

    # 3. Determine study days vs final revision day
    # If num_days > 1: Days 1..(num_days-1) are study days; Day num_days is final revision.
    # If num_days == 1: Day 1 is study with afternoon revision block.
    if num_days > 1:
        num_study_days = num_days - 1
        day_session_slices = partition_sessions_evenly(all_sessions, num_study_days)
    else:
        num_study_days = 1
        day_session_slices = [all_sessions]

    # 4. Schedule daily items
    days: List[Dict[str, Any]] = []

    for d in range(1, num_study_days + 1):
        sessions_for_day = day_session_slices[d - 1]
        day_items = schedule_study_day(
            day_num=d,
            sessions=sessions_for_day,
            is_single_day=(num_days == 1),
            start_minutes=540,  # 09:00
        )
        total_study_mins = sum(
            itm["duration_minutes"] for itm in day_items if itm["type"] in ("study", "revision")
        )
        date_label = "Day 1 (Today)" if d == 1 else f"Day {d}"
        days.append(
            {
                "day_number": d,
                "date_label": date_label,
                "total_study_minutes": total_study_mins,
                "items": day_items,
            }
        )

    # If num_days > 1, Day num_days is dedicated to final revision & paper solving
    if num_days > 1:
        final_day_num = num_days
        day_items = schedule_final_revision_day(day_num=final_day_num, start_minutes=540)
        total_study_mins = sum(
            itm["duration_minutes"] for itm in day_items if itm["type"] in ("study", "revision")
        )
        days.append(
            {
                "day_number": final_day_num,
                "date_label": f"Day {final_day_num}",
                "total_study_minutes": total_study_mins,
                "items": day_items,
            }
        )

    # 5. Workload analysis & Heavy Plan detection
    input_total_minutes = sum(get_item_duration(item) for item in raw_items)
    input_daily_hours = input_total_minutes / (60.0 * num_days)

    scheduled_total_minutes = sum(d["total_study_minutes"] for d in days)
    scheduled_daily_hours = scheduled_total_minutes / (60.0 * num_days)

    is_heavy_plan = (input_daily_hours > 6.5) or (scheduled_daily_hours > 6.5)

    if is_heavy_plan:
        reported_daily_hours = round(input_daily_hours if input_daily_hours > 0 else scheduled_daily_hours, 1)
        heavy_warning: Optional[str] = (
            f"This is a heavy plan: about {reported_daily_hours} hours/day. "
            f"Take frequent breaks and stay hydrated."
        )
    else:
        heavy_warning = None

    # 6. Extract answers dict if available
    answers: Dict[str, Any] = {}
    for item in raw_items:
        if "answer" in item and isinstance(item["answer"], dict):
            ans = item["answer"]
            ans_id = ans.get("id") or item.get("answer_id")
            if ans_id:
                answers[ans_id] = ans
        elif "answer_id" in item and item["answer_id"]:
            ans_id = str(item["answer_id"])
            answers[ans_id] = {
                "id": ans_id,
                "question_or_topic": get_item_title(item),
                "module": get_item_module(item),
                "content": item.get("content", ""),
                "source_type": item.get("source_type", "curriculum_grounded"),
                "source_attribution": item.get("source_attribution", ""),
                "source_urls": item.get("source_urls", []),
            }

    plan_id = f"plan_{uuid.uuid4().hex[:8]}"

    return {
        "plan_id": plan_id,
        "course_code": course_code,
        "course_title": course_title,
        "num_days": num_days,
        "num_modules": num_modules,
        "is_heavy_plan": is_heavy_plan,
        "heavy_warning": heavy_warning,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "answers": answers,
    }
