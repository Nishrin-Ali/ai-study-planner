"""
Unit tests for deterministic timetable scheduling engine.

Tests:
1. Single day (num_days=1, num_modules=1) checks session times, break, and recap.
2. Multi-day (num_days=3, num_modules=3) checks module continuity, breaks, lunch, and final day revision.
3. 10 days, 5 modules test.
4. Heavy plan detection when items demand > 6.5 hrs/day.
5. Verify no overlapping time intervals within any day.
6. Edge cases: long item splitting, validation errors, and empty items.
"""

import pytest

from backend.app.services.scheduler.engine import (
    generate_timetable,
    minutes_to_time,
    time_to_minutes,
)


def test_single_day_schedule():
    """
    Test 1: Single day (num_days=1, num_modules=1)
    Checks session times, break, and recap.
    """
    items = [
        {
            "id": "q1",
            "title": "Linear and Non-Linear Data Structures",
            "module": 1,
            "duration_minutes": 60,
            "answer_id": "ans_01",
        },
        {
            "id": "q2",
            "title": "Dynamic Memory Allocation & Pointers",
            "module": 1,
            "duration_minutes": 75,
            "answer_id": "ans_02",
        },
    ]

    plan = generate_timetable(
        num_days=1,
        num_modules=1,
        items_with_effort=items,
        course_code="BCS304",
        course_title="Data Structures and Applications",
    )

    assert plan["num_days"] == 1
    assert plan["num_modules"] == 1
    assert len(plan["days"]) == 1

    day1 = plan["days"][0]
    assert day1["day_number"] == 1
    assert day1["date_label"] == "Day 1 (Today)"
    items_d1 = day1["items"]
    assert len(items_d1) >= 3

    # Check day start time
    assert items_d1[0]["start_time"] == "09:00"

    # Check study sessions exist with valid durations
    study_items = [it for it in items_d1 if it["type"] == "study"]
    assert len(study_items) == 2
    for s in study_items:
        assert 45 <= s["duration_minutes"] <= 80
        assert s["module"] == 1
        assert s["answer_id"] in ["ans_01", "ans_02"]

    # Check break exists with 10-15 mins duration
    break_items = [it for it in items_d1 if it["type"] == "break"]
    assert len(break_items) >= 1
    for b in break_items:
        assert 10 <= b["duration_minutes"] <= 15

    # Check afternoon revision block exists (45 mins)
    revision_items = [it for it in items_d1 if it["type"] == "revision"]
    assert len(revision_items) == 1
    rev = revision_items[0]
    assert rev["duration_minutes"] == 45
    assert "Revision" in rev["title"] or "Recap" in rev["title"]

    # Verify answers mapping
    assert "ans_01" in plan["answers"]
    assert "ans_02" in plan["answers"]


def test_multi_day_schedule():
    """
    Test 2: Multi-day (num_days=3, num_modules=3)
    Checks module continuity, breaks, lunch, and final day revision.
    """
    # Deliberately out of module order in input to test module contiguity sorting
    items = [
        {"title": "Queue ADT & Circular Queue", "module": 2, "duration_minutes": 60},
        {"title": "Priority Queue Implementation", "module": 2, "duration_minutes": 60},
        {"title": "Arrays & Dynamic Memory Allocation", "module": 1, "duration_minutes": 75},
        {"title": "Stack ADT & Expression Evaluation", "module": 1, "duration_minutes": 75},
        {"title": "Singly Linked List Operations", "module": 3, "duration_minutes": 75},
        {"title": "Doubly Linked List & Applications", "module": 3, "duration_minutes": 60},
    ]

    plan = generate_timetable(
        num_days=3,
        num_modules=3,
        items_with_effort=items,
        course_code="BCS304",
        course_title="Data Structures and Applications",
    )

    assert plan["num_days"] == 3
    assert len(plan["days"]) == 3

    # Check Module Continuity across study days (Days 1 and 2)
    study_items = []
    for d in plan["days"][:2]:
        for it in d["items"]:
            if it["type"] == "study":
                study_items.append(it)

    modules_observed = [it["module"] for it in study_items]
    assert len(modules_observed) == 6
    # Ensure module numbers are monotonically non-decreasing (Module 1 before 2 before 3)
    for i in range(len(modules_observed) - 1):
        assert modules_observed[i] <= modules_observed[i + 1]

    # Check Breaks on study days
    for d in plan["days"][:2]:
        breaks = [it for it in d["items"] if it["type"] == "break"]
        assert len(breaks) >= 1
        for b in breaks:
            assert 10 <= b["duration_minutes"] <= 15

    # Check Lunch presence on study days around 13:00
    for d in plan["days"][:2]:
        lunch_items = [it for it in d["items"] if it["type"] == "lunch"]
        assert len(lunch_items) == 1
        lunch = lunch_items[0]
        assert 30 <= lunch["duration_minutes"] <= 45
        lunch_start_mins = time_to_minutes(lunch["start_time"])
        # Should be between 12:00 and 13:30
        assert time_to_minutes("12:00") <= lunch_start_mins <= time_to_minutes("13:30")

    # Check Daily Recap on Days 1 and 2 (Days 1 to N-1)
    for d in plan["days"][:2]:
        recap_items = [it for it in d["items"] if it["type"] == "revision"]
        assert len(recap_items) == 1
        assert recap_items[0]["duration_minutes"] == 30

    # Check Final Day (Day 3) is dedicated to revision & paper solving
    day3 = plan["days"][2]
    assert day3["day_number"] == 3
    # No regular 'study' items on final day, only revision, lunch, and breaks
    day3_types = set(it["type"] for it in day3["items"])
    assert "study" not in day3_types
    assert "revision" in day3_types
    assert "lunch" in day3_types
    assert "break" in day3_types

    day3_revisions = [it for it in day3["items"] if it["type"] == "revision"]
    assert len(day3_revisions) >= 4  # multiple revision & question paper solving blocks
    paper_solving = [it for it in day3_revisions if "Question Paper" in it["title"] or "Question Bank" in it["title"]]
    assert len(paper_solving) >= 1


def test_ten_days_five_modules_schedule():
    """
    Test 3: 10 days, 5 modules test.
    Checks 10-day distribution, module contiguity across 9 study days,
    and final 10th day dedicated revision.
    """
    items = []
    for mod in range(1, 6):
        items.append({"title": f"Module {mod} Core Concepts", "module": mod, "duration_minutes": 60})
        items.append({"title": f"Module {mod} Numerical & Practice", "module": mod, "duration_minutes": 60})

    plan = generate_timetable(
        num_days=10,
        num_modules=5,
        items_with_effort=items,
        course_code="BCS301",
        course_title="Mathematics for Computer Science",
    )

    assert plan["num_days"] == 10
    assert len(plan["days"]) == 10

    # Days 1 to 9 are study days with daily recaps
    study_day_modules = []
    for d_idx in range(9):
        day = plan["days"][d_idx]
        assert day["day_number"] == d_idx + 1
        # Each study day must start at 09:00
        assert day["items"][0]["start_time"] == "09:00"
        # Each study day has a 30-min recap
        recap = [it for it in day["items"] if it["type"] == "revision"]
        assert len(recap) >= 1
        assert recap[-1]["duration_minutes"] == 30

        for it in day["items"]:
            if it["type"] == "study" and it["module"] is not None:
                study_day_modules.append(it["module"])

    # Verify module contiguity across all 9 study days
    for i in range(len(study_day_modules) - 1):
        assert study_day_modules[i] <= study_day_modules[i + 1]

    # Day 10 is the dedicated full syllabus revision day
    day10 = plan["days"][9]
    assert day10["day_number"] == 10
    day10_types = set(it["type"] for it in day10["items"])
    assert "study" not in day10_types
    assert "revision" in day10_types
    assert "lunch" in day10_types


def test_heavy_plan_warning_detection():
    """
    Test 4: Heavy plan detection when items demand > 6.5 hrs/day.
    Checks trigger, warning message format, and light plan non-trigger.
    """
    # 1. Heavy single day plan (> 6.5 hours = 390 mins)
    heavy_items_1day = [
        {"title": f"Heavy Topic {i}", "module": 1, "duration_minutes": 70}
        for i in range(6)  # 6 * 70 = 420 mins = 7.0 hours
    ]
    plan_heavy_1day = generate_timetable(
        num_days=1,
        num_modules=1,
        items_with_effort=heavy_items_1day,
    )
    assert plan_heavy_1day["is_heavy_plan"] is True
    assert plan_heavy_1day["heavy_warning"] is not None
    assert "This is a heavy plan" in plan_heavy_1day["heavy_warning"]
    assert "hours/day" in plan_heavy_1day["heavy_warning"]
    assert "hydrated" in plan_heavy_1day["heavy_warning"]

    # 2. Light plan (not heavy, ~2 hours)
    light_items = [
        {"title": "Light Topic 1", "module": 1, "duration_minutes": 60},
        {"title": "Light Topic 2", "module": 1, "duration_minutes": 60},
    ]
    plan_light = generate_timetable(
        num_days=1,
        num_modules=1,
        items_with_effort=light_items,
    )
    assert plan_light["is_heavy_plan"] is False
    assert plan_light["heavy_warning"] is None

    # 3. Multi-day heavy plan (3 days, 24 hours of study = 8 hours/day)
    heavy_items_3days = [
        {"title": f"Heavy Multi Topic {i}", "module": (i % 3) + 1, "duration_minutes": 60}
        for i in range(24)  # 24 * 60 = 1440 mins = 24 hrs / 3 = 8.0 hrs/day
    ]
    plan_heavy_3days = generate_timetable(
        num_days=3,
        num_modules=3,
        items_with_effort=heavy_items_3days,
    )
    assert plan_heavy_3days["is_heavy_plan"] is True
    assert plan_heavy_3days["heavy_warning"] is not None
    assert "about 8" in plan_heavy_3days["heavy_warning"]


def test_no_overlapping_time_intervals():
    """
    Test 5: Verify no overlapping time intervals within any day.
    Tests across 1 day, 2 days, 3 days, 5 days, and 10 days configurations.
    Verifies every item has start_time < end_time and item[i].end_time == item[i+1].start_time.
    """
    test_cases = [
        (1, 1, [{"title": "T1", "duration_minutes": 60, "module": 1}]),
        (2, 2, [{"title": f"T{i}", "duration_minutes": 60, "module": (i % 2) + 1} for i in range(4)]),
        (3, 3, [{"title": f"T{i}", "duration_minutes": 75, "module": (i % 3) + 1} for i in range(6)]),
        (5, 3, [{"title": f"T{i}", "duration_minutes": 60, "module": (i % 3) + 1} for i in range(8)]),
        (10, 5, [{"title": f"T{i}", "duration_minutes": 60, "module": (i % 5) + 1} for i in range(12)]),
    ]

    for num_days, num_modules, items in test_cases:
        plan = generate_timetable(
            num_days=num_days,
            num_modules=num_modules,
            items_with_effort=items,
        )

        assert len(plan["days"]) == num_days

        for day in plan["days"]:
            items_list = day["items"]
            assert len(items_list) > 0, f"Day {day['day_number']} has no items."

            # Verify day starts at 09:00
            assert items_list[0]["start_time"] == "09:00"

            for i, itm in enumerate(items_list):
                start_m = time_to_minutes(itm["start_time"])
                end_m = time_to_minutes(itm["end_time"])

                # Each item has positive duration matching duration_minutes
                assert end_m > start_m, f"Item {itm['id']} has invalid end <= start"
                assert end_m - start_m == itm["duration_minutes"], (
                    f"Item {itm['id']} duration mismatch: {end_m - start_m} != {itm['duration_minutes']}"
                )

                # Strict time continuity: no gaps, no overlaps
                if i < len(items_list) - 1:
                    next_itm = items_list[i + 1]
                    assert itm["end_time"] == next_itm["start_time"], (
                        f"Overlap or gap between item {itm['id']} ({itm['end_time']}) "
                        f"and {next_itm['id']} ({next_itm['start_time']})"
                    )


def test_long_item_splitting():
    """
    Test splitting items with duration > 80 mins into balanced ~45-80 min chunks.
    """
    long_item = [
        {"title": "Complex Graph Algorithms", "module": 2, "duration_minutes": 150, "answer_id": "ans_graph"}
    ]

    plan = generate_timetable(num_days=1, num_modules=1, items_with_effort=long_item)
    day1_items = plan["days"][0]["items"]
    study_items = [it for it in day1_items if it["type"] == "study"]

    # 150 mins should be split into 2 chunks of 75 mins each
    assert len(study_items) == 2
    assert study_items[0]["duration_minutes"] == 75
    assert study_items[1]["duration_minutes"] == 75
    assert "Part 1" in study_items[0]["title"]
    assert "Part 2" in study_items[1]["title"]
    assert study_items[0]["answer_id"] == "ans_graph"
    assert study_items[1]["answer_id"] == "ans_graph"


def test_validation_and_edge_cases():
    """
    Test edge cases and validation: invalid num_days or num_modules, and empty items.
    """
    with pytest.raises(ValueError, match="num_days must be between 1 and 10"):
        generate_timetable(num_days=0, num_modules=1)

    with pytest.raises(ValueError, match="num_days must be between 1 and 10"):
        generate_timetable(num_days=11, num_modules=1)

    with pytest.raises(ValueError, match="num_modules must be at least 1"):
        generate_timetable(num_days=3, num_modules=0)

    # Empty items list should generate valid schedule with self-paced placeholders
    plan_empty = generate_timetable(num_days=2, num_modules=1, items_with_effort=[])
    assert plan_empty["num_days"] == 2
    assert len(plan_empty["days"]) == 2
    assert plan_empty["days"][0]["items"][0]["start_time"] == "09:00"
