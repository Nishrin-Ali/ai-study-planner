---
name: study-scheduler
description: Deterministic timetable engine rules, breaks, revision scheduling, and unit tests
---

# Study Scheduler Skill

Rules for deterministic timetable generation without hallucinated or floating time gaps.

## 1. Parameters & Limits
- Day start time: `09:00`.
- Max realistic study hours: 6 to 7 hours per day.
- If total estimated time divided by `num_days` exceeds 6.5 hours/day, flag `is_heavy_plan = True` and emit a warning:
  `"This is a heavy plan: about {round(daily_hours, 1)} hours/day. Take frequent breaks and stay hydrated."`
- Topics should remain contiguous per module (e.g. all Module 1 items together, followed by Module 2, etc.).

## 2. Daily Block Distribution
- Study Session: 45 to 80 minutes.
- Break: 10 to 15 minutes after each study session.
- Midday Lunch: 30 to 45 minutes around 13:00 (1:00 PM).
- End of Day: Wrap up before 19:00 (7:00 PM) where possible.

## 3. Revision Logic
- If `num_days > 1`:
  - Last day (Day `N`) is reserved exclusively for comprehensive revision and past question practice.
  - Days 1 to `N-1` feature a 30-minute end-of-day recap session.
- If `num_days == 1`:
  - Afternoon features a dedicated 45-minute revision block for covered modules.

## 4. Item Schema
```python
class TimetableItem(BaseModel):
    id: str
    day_number: int
    type: Literal["study", "break", "lunch", "revision"]
    module: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_time: str # "09:00"
    end_time: str   # "10:15"
    duration_minutes: int
    answer_id: Optional[str] = None
    is_completed: bool = False
```
