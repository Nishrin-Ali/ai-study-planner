// Unit test and test harness for ReminderService
import test from 'node:test';
import assert from 'node:assert/strict';

// Mock Web Browser Environment for Node.js test runner
const localStorageMock: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => localStorageMock[k] || null,
  setItem: (k: string, v: string) => {
    localStorageMock[k] = v;
  },
  removeItem: (k: string) => {
    delete localStorageMock[k];
  },
  clear: () => {
    for (const k in localStorageMock) delete localStorageMock[k];
  },
  get length() {
    return Object.keys(localStorageMock).length;
  },
  key: (i: number) => Object.keys(localStorageMock)[i] || null,
};

(globalThis as any).window = globalThis;
(globalThis as any).document = {
  addEventListener: () => {},
  visibilityState: 'visible',
};
try {
  Object.defineProperty(globalThis, 'navigator', {
    value: { serviceWorker: undefined },
    configurable: true,
    writable: true,
  });
} catch {
  // navigator is defined
}
function MockNotification(title: string, options?: any) {
  (this as any).title = title;
  (this as any).options = options;
}
(MockNotification as any).permission = 'granted';
(MockNotification as any).requestPermission = async () => 'granted';
(globalThis as any).Notification = MockNotification;

// Import ReminderService
import { ReminderService } from './reminders.ts';
import type { ReminderNotification } from './reminders.ts';

test('1. ReminderService initializes cleanly with timezone support', () => {
  const service = new ReminderService();
  const tz = service.getLocalTimeZone();
  const tzOffset = service.getTimezoneOffsetString();

  assert.ok(tz.length > 0, 'Local timezone should be resolved');
  assert.match(tzOffset, /^[+-]\d{2}:\d{2}$/, 'Timezone offset format is valid');
});

test('2. scheduleDayItems generates exact required messages and start/end events', () => {
  const service = new ReminderService();
  service.resetFiredCache();

  const mockItems = [
    {
      id: 'item_mod1',
      type: 'study',
      module: 2,
      start_time: '10:00',
      end_time: '11:00',
      duration_minutes: 60,
      title: 'Module 2: Binary Search Trees',
    },
    {
      id: 'item_break1',
      type: 'break',
      module: null,
      start_time: '11:00',
      end_time: '11:15',
      duration_minutes: 15,
      title: 'Break',
    },
    {
      id: 'item_rev1',
      type: 'revision',
      module: 2,
      start_time: '11:15',
      end_time: '11:45',
      duration_minutes: 30,
      title: 'Module 2 Revision',
    },
  ];

  service.scheduleDayItems(mockItems, 'plan_vtu_101', 1);
  const scheduled = service.getScheduledItems();

  // 3 items * 2 events (start and end) = 6 events
  assert.equal(scheduled.length, 6, 'Should schedule exactly 6 events (start + end per item)');

  // Verify Module Study Session Start message
  const modStart = scheduled.find((s) => s.itemId === 'item_mod1' && s.eventType === 'start');
  assert.ok(modStart);
  assert.equal(modStart.title, 'Module 2 Study Session Started');
  assert.equal(modStart.body, 'Your Module 2 study session has started!');

  // Verify Module Study Session End message
  const modEnd = scheduled.find((s) => s.itemId === 'item_mod1' && s.eventType === 'end');
  assert.ok(modEnd);
  assert.equal(modEnd.title, 'Module 2 Session Ended');
  assert.equal(modEnd.body, 'Your Module 2 study session has ended. Well done!');

  // Verify Break Start message
  const breakStart = scheduled.find((s) => s.itemId === 'item_break1' && s.eventType === 'start');
  assert.ok(breakStart);
  assert.equal(breakStart.title, 'Time for a 15-minute break!');
  assert.equal(breakStart.body, 'Time for a 15-minute break. Take some rest!');

  // Verify Break End message
  const breakEnd = scheduled.find((s) => s.itemId === 'item_break1' && s.eventType === 'end');
  assert.ok(breakEnd);
  assert.equal(breakEnd.title, 'Break is over');
  assert.equal(breakEnd.body, "Your break is over. Let's get back to studying!");

  // Verify Revision Start and End
  const revStart = scheduled.find((s) => s.itemId === 'item_rev1' && s.eventType === 'start');
  assert.ok(revStart);
  assert.equal(revStart.body, 'Your Module 2 revision session has started!');

  const revEnd = scheduled.find((s) => s.itemId === 'item_rev1' && s.eventType === 'end');
  assert.ok(revEnd);
  assert.equal(revEnd.body, 'Your Module 2 revision session has ended. Well done!');
});

test('3. Ticker and 60-second catch-up window fires events exactly once', async () => {
  const service = new ReminderService();
  service.resetFiredCache();

  const receivedNotifications: ReminderNotification[] = [];
  service.subscribe((n) => {
    receivedNotifications.push(n);
  });

  const baseDate = new Date();
  baseDate.setHours(9, 0, 0, 0);

  const mockItems = [
    {
      id: 'session_catchup',
      type: 'study',
      module: 1,
      start_time: '09:00',
      end_time: '10:00',
      duration_minutes: 60,
      title: 'Module 1 Study',
    },
  ];

  // Schedule with baseDate = 09:00:00
  service.scheduleDayItems(mockItems, 'plan_catchup_test', 1, baseDate);

  const startEventId = 'fired_plan_catchup_test_session_catchup_start';

  // Simulating time: 09:00:25 (25 seconds after scheduled start => within 60s window)
  const simTimeWithin60s = baseDate.getTime() + 25000;
  service.tick(simTimeWithin60s);

  assert.equal(receivedNotifications.length, 1, 'Should fire notification within 60s window');
  assert.equal(receivedNotifications[0].title, 'Module 1 Study Session Started');
  assert.ok(service.isFired(startEventId), 'Event should be marked fired');
  assert.ok(localStorageMock[startEventId], 'Event ID should be stored in localStorage');

  // Second tick at 09:00:30 (should NOT fire again - deduplication)
  service.tick(simTimeWithin60s + 5000);
  assert.equal(receivedNotifications.length, 1, 'Event must not fire a second time');
});

test('4. Events older than 60 seconds are marked expired and not fired', () => {
  const service = new ReminderService();
  service.resetFiredCache();

  const receivedNotifications: ReminderNotification[] = [];
  service.subscribe((n) => {
    receivedNotifications.push(n);
  });

  const baseDate = new Date();
  baseDate.setHours(8, 0, 0, 0);

  const mockItems = [
    {
      id: 'session_stale',
      type: 'study',
      module: 3,
      start_time: '07:00',
      end_time: '07:50',
      duration_minutes: 50,
      title: 'Stale Morning Session',
    },
  ];

  service.scheduleDayItems(mockItems, 'plan_stale_test', 1, baseDate);

  const startEventId = 'fired_plan_stale_test_session_stale_start';

  // Simulating current time 08:05:00 (outside 60s catchup window)
  const simTimeStale = baseDate.getTime() + 300000;
  service.tick(simTimeStale);

  assert.equal(receivedNotifications.length, 0, 'Stale event older than 60s must NOT fire notification');
  assert.ok(service.isFired(startEventId), 'Stale event should be marked expired/fired to prevent re-checking');
});

test('5. Sound alert toggle persists in localStorage', () => {
  const service = new ReminderService();
  service.setSoundEnabled(false);
  assert.equal(service.isSoundEnabled(), false);

  service.setSoundEnabled(true);
  assert.equal(service.isSoundEnabled(), true);
  assert.equal(localStorageMock['vtu_sound_alerts_enabled'], 'true');

  service.setSoundEnabled(false);
  assert.equal(service.isSoundEnabled(), false);
  assert.equal(localStorageMock['vtu_sound_alerts_enabled'], 'false');
});

test('6. notify() dispatches in-app toast for test reminder', async () => {
  const service = new ReminderService();
  let received: ReminderNotification | null = null;
  service.subscribe((n) => {
    received = n;
  });

  await service.notify(
    'Test Reminder: Break Time',
    'Time for a 15-minute break. Take some rest!',
    'break'
  );

  assert.ok(received);
  assert.equal((received as ReminderNotification).title, 'Test Reminder: Break Time');
  assert.equal((received as ReminderNotification).body, 'Time for a 15-minute break. Take some rest!');
  assert.equal((received as ReminderNotification).type, 'break');
});
