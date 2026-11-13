---
name: browser-reminders
description: Browser Notification API, Service Worker registration, in-app countdown banner and audio/toast fallbacks
---

# Browser Reminders Skill

Reliable web-based study and break notifications with multiple fallback layers.

## 1. Permission Flow
- Trigger `Notification.requestPermission()` ONLY when the user explicitly clicks the "Enable Reminders" button.
- Check states:
  - `granted`: Register Service Worker or start Web Notifications schedule.
  - `denied`: Inform user clearly: "Notifications blocked. In-app alerts will be displayed while this tab is active."
  - `default`: Prompt user.

## 2. Notification Timing & Rescheduling
- On timetable load, calculate timestamps for each session start/end and break start/end.
- Skip timestamps that have already elapsed in the past today.
- Set accurate timeouts (`setTimeout` / Service Worker alarms).

## 3. Standard Messages
- Session Start:
  `"Your Module {module} study session has started!"`
- Session End:
  `"Your Module {module} study session has ended. Well done!"`
- Break Start:
  `"Time for a {duration}-minute break. Take some rest!"`
- Break End:
  `"Your break is over. Let's get back to studying!"`

## 4. In-App Fallback & Active Status Bar
- Display a sticky top strip:
  - **Now**: Currently active item (e.g. "Module 2: Binary Search Trees") + remaining time countdown.
  - **Next Up**: Upcoming item & time (e.g. "Next: 15-min break at 11:30").
- Provide a "Send test reminder" button in the UI for instant verification.
