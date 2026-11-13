// Web Notifications & In-App Toast Reminders Manager
// Resilient 1-second ticker, catch-up mechanism, Web Audio chime, and SW dual dispatch

export type ReminderType = 'start' | 'end' | 'break' | 'revision' | 'test';

export interface ReminderNotification {
  id?: string;
  title: string;
  body: string;
  type: ReminderType;
  timestamp?: number;
}

export type ReminderCallback = (notification: ReminderNotification) => void;

export interface ScheduledReminderItem {
  id: string; // Fired identifier e.g. fired_${planId}_${itemId}_${eventType}
  planId: string;
  itemId: string;
  eventType: 'start' | 'end';
  scheduledTimestamp: number; // Absolute epoch timestamp ms
  title: string;
  body: string;
  type: ReminderType;
  module?: number | null;
  durationMinutes?: number;
}

export interface SimulationState {
  isRunning: boolean;
  step: 'idle' | 'study' | 'break' | 'done';
  secondsLeft: number;
}

// Web Audio API Soft Chime Generator
export class ChimePlayer {
  private ctx: AudioContext | null = null;
  private readonly storageKey = 'vtu_sound_alerts_enabled';

  isSoundEnabled(): boolean {
    if (typeof window === 'undefined' || !window.localStorage) return false;
    return localStorage.getItem(this.storageKey) === 'true';
  }

  setSoundEnabled(enabled: boolean): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem(this.storageKey, enabled ? 'true' : 'false');
    }
  }

  playChime(): void {
    if (!this.isSoundEnabled()) return;
    if (typeof window === 'undefined') return;

    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;

      if (!this.ctx || this.ctx.state === 'closed') {
        this.ctx = new AudioCtx();
      }

      if (this.ctx.state === 'suspended') {
        this.ctx.resume().catch(() => {});
      }

      const ctx = this.ctx;
      const now = ctx.currentTime;

      // Soft dual harmonic sine wave (E5 = 659.25Hz -> A5 = 880Hz)
      const notes = [
        { freq: 659.25, startOffset: 0.0, duration: 0.22 },
        { freq: 880.0, startOffset: 0.12, duration: 0.38 },
      ];

      notes.forEach(({ freq, startOffset, duration }) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + startOffset);

        // Smooth attack and decay envelope
        gain.gain.setValueAtTime(0.0001, now + startOffset);
        gain.gain.exponentialRampToValueAtTime(0.12, now + startOffset + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + startOffset + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + startOffset);
        osc.stop(now + startOffset + duration + 0.05);
      });
    } catch (err) {
      console.warn('Audio chime playback failed:', err);
    }
  }
}

export class ReminderService {
  private scheduledItems: ScheduledReminderItem[] = [];
  private listeners: ReminderCallback[] = [];
  private tickerId: number | null = null;
  private firedIds: Set<string> = new Set();
  private chimePlayer = new ChimePlayer();
  private simulationTimer: number | null = null;

  constructor() {
    this.initFiredCache();
    this.registerServiceWorker();
    this.startTicker();
    this.setupCatchupListeners();
  }

  // Load fired keys from localStorage to prevent duplicate firing across reloads
  private initFiredCache() {
    if (typeof window === 'undefined' || !window.localStorage) return;
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('fired_')) {
          this.firedIds.add(key);
        }
      }
    } catch (e) {
      console.warn('Could not read localStorage for fired reminders:', e);
    }
  }

  // Timezone helpers
  getLocalTimeZone(): string {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
    } catch {
      return 'Asia/Kolkata';
    }
  }

  getTimezoneOffsetString(): string {
    const offsetMinutes = -new Date().getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? '+' : '-';
    const pad = (n: number) => String(Math.floor(Math.abs(n))).padStart(2, '0');
    const h = pad(offsetMinutes / 60);
    const m = pad(offsetMinutes % 60);
    return `${sign}${h}:${m}`;
  }

  isSoundEnabled(): boolean {
    return this.chimePlayer.isSoundEnabled();
  }

  setSoundEnabled(enabled: boolean): void {
    this.chimePlayer.setSoundEnabled(enabled);
    if (enabled) {
      // Gentle preview chime on activation
      this.chimePlayer.playChime();
    }
  }

  playChime(): void {
    this.chimePlayer.playChime();
  }

  async registerServiceWorker() {
    if (typeof window !== 'undefined' && typeof navigator !== 'undefined' && navigator.serviceWorker?.register) {
      try {
        await navigator.serviceWorker.register('/sw.js');
      } catch (err) {
        console.warn('Service worker registration failed:', err);
      }
    }
  }

  async requestPermission(): Promise<NotificationPermission> {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return 'denied';
    }
    const result = await Notification.requestPermission();
    return result;
  }

  getPermission(): NotificationPermission {
    if (typeof window === 'undefined' || !('Notification' in window)) return 'denied';
    return Notification.permission;
  }

  subscribe(callback: ReminderCallback): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  // Check if reminder was already fired in this session or stored in localStorage
  isFired(id: string): boolean {
    if (this.firedIds.has(id)) return true;
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem(id) !== null;
    }
    return false;
  }

  markFired(id: string): void {
    this.firedIds.add(id);
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        localStorage.setItem(id, Date.now().toString());
      } catch (e) {
        console.warn('Failed to persist fired reminder in localStorage:', e);
      }
    }
  }

  // Unified dual dispatch: SW showNotification + Notification fallback + In-app Toast + Chime
  async notify(
    title: string,
    body: string,
    type: ReminderType = 'start',
    eventId?: string
  ): Promise<void> {
    // 1. Play soft audio chime (if user enabled it)
    this.chimePlayer.playChime();

    // 2. ALWAYS dispatch in-app toast event
    const notifPayload: ReminderNotification = {
      id: eventId || `toast_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      title,
      body,
      type,
      timestamp: Date.now(),
    };
    this.listeners.forEach((cb) => {
      try {
        cb(notifPayload);
      } catch (err) {
        console.error('Toast listener error:', err);
      }
    });

    // 3. Browser native notification (Dual dispatch: Service Worker primary, Notification constructor fallback)
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      let swDispatched = false;

      if ('serviceWorker' in navigator && navigator.serviceWorker?.getRegistration) {
        try {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg) {
            if (typeof reg.showNotification === 'function') {
              await reg.showNotification(title, {
                body,
                icon: '/favicon.svg',
                badge: '/favicon.svg',
                tag: eventId || `vtu_reminder_${Date.now()}`,
              });
              swDispatched = true;
            } else if (navigator.serviceWorker.controller) {
              navigator.serviceWorker.controller.postMessage({
                type: 'SHOW_NOTIFICATION',
                title,
                options: {
                  body,
                  tag: eventId || `vtu_reminder_${Date.now()}`,
                },
              });
              swDispatched = true;
            }
          }
        } catch (err) {
          console.warn('Service Worker showNotification failed, using fallback:', err);
        }
      }

      if (!swDispatched) {
        try {
          new Notification(title, {
            body,
            icon: '/favicon.svg',
            tag: eventId || `vtu_reminder_${Date.now()}`,
          });
        } catch (err) {
          console.warn('Native Notification fallback failed:', err);
        }
      }
    }
  }

  // 1-Second Interval Ticker
  private startTicker() {
    if (typeof window === 'undefined') return;
    if (this.tickerId !== null) return;

    this.tickerId = window.setInterval(() => {
      this.tick();
    }, 1000);
  }

  // Catch-up listeners: triggered when tab regains focus or visibility
  private setupCatchupListeners() {
    if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          this.catchUp();
        }
      });
    }

    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('focus', () => {
        this.catchUp();
      });
    }
  }

  // Process ticker check against absolute Date.now()
  tick(currentTimeMs: number = Date.now()): void {
    const now = currentTimeMs;

    for (const item of this.scheduledItems) {
      if (this.isFired(item.id)) continue;

      const elapsed = now - item.scheduledTimestamp;

      // Case A: Event scheduled time has arrived within the 60-second catch-up window
      if (elapsed >= 0 && elapsed <= 60000) {
        this.markFired(item.id);
        this.notify(item.title, item.body, item.type, item.id);
      }
      // Case B: Event elapsed more than 60 seconds ago (stale, e.g. scheduled hours ago before opening app)
      else if (elapsed > 60000) {
        this.markFired(item.id);
      }
    }
  }

  // Catch-up method: immediately check and fire any event whose scheduled time elapsed within last 60s
  catchUp(nowTimeMs: number = Date.now()): void {
    this.tick(nowTimeMs);
  }

  clearScheduled(): void {
    this.scheduledItems = [];
    if (this.simulationTimer !== null) {
      window.clearTimeout(this.simulationTimer);
      this.simulationTimer = null;
    }
  }

  // Schedule timetable items for a given plan and day
  scheduleDayItems(
    items: Array<{
      id?: string;
      type: string;
      module: number | null;
      start_time: string;
      end_time: string;
      duration_minutes: number;
      title: string;
    }>,
    planId: string = 'current_plan',
    dayNumber: number = 1,
    baseDate: Date = new Date()
  ): void {
    this.clearScheduled();

    const dayOffset = Math.max(0, dayNumber - 1);

    items.forEach((item, index) => {
      const itemId = item.id || `item_${dayNumber}_${index}`;

      // Calculate absolute start & end timestamps in local time
      const [startH, startM] = item.start_time.split(':').map(Number);
      const [endH, endM] = item.end_time.split(':').map(Number);

      const startDate = new Date(baseDate.getTime());
      startDate.setDate(startDate.getDate() + dayOffset);
      startDate.setHours(startH, startM, 0, 0);

      const endDate = new Date(baseDate.getTime());
      endDate.setDate(endDate.getDate() + dayOffset);
      endDate.setHours(endH, endM, 0, 0);

      const startTimestamp = startDate.getTime();
      const endTimestamp = endDate.getTime();

      // Configure start event
      let startTitle = '';
      let startBody = '';
      let startType: ReminderType = 'start';

      if (item.type === 'study') {
        startTitle = item.module ? `Module ${item.module} Study Session Started` : 'Study Session Started';
        startBody = item.module
          ? `Your Module ${item.module} study session has started!`
          : 'Your study session has started!';
        startType = 'start';
      } else if (item.type === 'break' || item.type === 'lunch') {
        const breakLabel = item.type === 'lunch' ? 'Lunch' : 'Break';
        startTitle = `Time for a ${item.duration_minutes}-minute break!`;
        startBody = `Time for a ${item.duration_minutes}-minute break. Take some rest!`;
        startType = 'break';
      } else if (item.type === 'revision') {
        startTitle = 'Revision Session Started';
        startBody = item.module
          ? `Your Module ${item.module} revision session has started!`
          : 'Your revision session has started!';
        startType = 'revision';
      }

      const startEventId = `fired_${planId}_${itemId}_start`;
      this.scheduledItems.push({
        id: startEventId,
        planId,
        itemId,
        eventType: 'start',
        scheduledTimestamp: startTimestamp,
        title: startTitle,
        body: startBody,
        type: startType,
        module: item.module,
        durationMinutes: item.duration_minutes,
      });

      // Configure end event
      let endTitle = '';
      let endBody = '';
      let endType: ReminderType = 'end';

      if (item.type === 'study') {
        endTitle = item.module ? `Module ${item.module} Session Ended` : 'Study Session Ended';
        endBody = item.module
          ? `Your Module ${item.module} study session has ended. Well done!`
          : 'Your study session has ended. Well done!';
        endType = 'end';
      } else if (item.type === 'break' || item.type === 'lunch') {
        endTitle = 'Break is over';
        endBody = "Your break is over. Let's get back to studying!";
        endType = 'end';
      } else if (item.type === 'revision') {
        endTitle = 'Revision Session Ended';
        endBody = item.module
          ? `Your Module ${item.module} revision session has ended. Well done!`
          : 'Your revision session has ended. Well done!';
        endType = 'end';
      }

      const endEventId = `fired_${planId}_${itemId}_end`;
      this.scheduledItems.push({
        id: endEventId,
        planId,
        itemId,
        eventType: 'end',
        scheduledTimestamp: endTimestamp,
        title: endTitle,
        body: endBody,
        type: endType,
        module: item.module,
        durationMinutes: item.duration_minutes,
      });
    });

    // Run catch-up right away on page load / timetable schedule
    this.catchUp(baseDate.getTime());
  }

  // Simulation test helper: allows fast demonstration of start -> break -> end transitions
  simulateSession(
    moduleNumber: number = 1,
    studySeconds: number = 5,
    breakSeconds: number = 5,
    onStateChange?: (state: SimulationState) => void
  ): () => void {
    if (this.simulationTimer !== null) {
      window.clearTimeout(this.simulationTimer);
      this.simulationTimer = null;
    }

    let currentStep: 'idle' | 'study' | 'break' | 'done' = 'study';
    let timeLeft = studySeconds;

    const report = () => {
      if (onStateChange) {
        onStateChange({
          isRunning: currentStep !== 'done' && currentStep !== 'idle',
          step: currentStep,
          secondsLeft: timeLeft,
        });
      }
    };

    // 1. Session start immediately
    this.notify(
      `Module ${moduleNumber} Study Session Started`,
      `Your Module ${moduleNumber} study session has started!`,
      'start'
    );
    report();

    const interval = window.setInterval(() => {
      timeLeft--;
      if (timeLeft > 0) {
        report();
        return;
      }

      if (currentStep === 'study') {
        // Study session ended, transition to break
        this.notify(
          `Module ${moduleNumber} Session Ended`,
          `Your Module ${moduleNumber} study session has ended. Well done!`,
          'end'
        );
        this.notify(
          `Time for a ${breakSeconds}-minute break!`,
          `Time for a ${breakSeconds}-minute break. Take some rest!`,
          'break'
        );
        currentStep = 'break';
        timeLeft = breakSeconds;
        report();
      } else if (currentStep === 'break') {
        // Break ended
        this.notify(
          'Break is over',
          "Your break is over. Let's get back to studying!",
          'end'
        );
        currentStep = 'done';
        timeLeft = 0;
        report();
        window.clearInterval(interval);
      }
    }, 1000);

    const cancelFn = () => {
      window.clearInterval(interval);
      currentStep = 'idle';
      timeLeft = 0;
      report();
    };

    return cancelFn;
  }

  // Reset all fired reminders in localStorage (for test or fresh re-run)
  resetFiredCache(): void {
    this.firedIds.clear();
    if (typeof window !== 'undefined' && window.localStorage) {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('fired_')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    }
  }

  // Getters for test verification
  getScheduledItems(): ScheduledReminderItem[] {
    return [...this.scheduledItems];
  }

  getFiredIds(): string[] {
    return Array.from(this.firedIds);
  }
}

export const reminderService = new ReminderService();
