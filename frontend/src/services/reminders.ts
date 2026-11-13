// Web Notifications & In-App Toast Reminders Manager

export type ReminderCallback = (notification: { title: string; body: string; type: string }) => void;

class ReminderService {
  private activeTimeouts: number[] = [];
  private listeners: ReminderCallback[] = [];

  constructor() {
    this.registerServiceWorker();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        await navigator.serviceWorker.register('/sw.js');
      } catch (err) {
        console.warn('Service worker registration failed:', err);
      }
    }
  }

  async requestPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      return 'denied';
    }
    return await Notification.requestPermission();
  }

  getPermission(): NotificationPermission {
    if (!('Notification' in window)) return 'denied';
    return Notification.permission;
  }

  subscribe(callback: ReminderCallback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  notify(title: string, body: string, type: 'start' | 'end' | 'break' | 'test' = 'start') {
    // 1. In-app toast listeners
    this.listeners.forEach((cb) => cb({ title, body, type }));

    // 2. Browser native notification
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: 'SHOW_NOTIFICATION',
            title,
            options: { body, icon: '/favicon.ico' },
          });
        } else {
          new Notification(title, { body });
        }
      } catch (e) {
        console.warn('Native notification failed:', e);
      }
    }
  }

  clearScheduled() {
    this.activeTimeouts.forEach((id) => window.clearTimeout(id));
    this.activeTimeouts = [];
  }

  scheduleDayItems(items: Array<{ type: string; module: number | null; start_time: string; end_time: string; duration_minutes: number; title: string }>) {
    this.clearScheduled();
    const now = new Date();

    items.forEach((item) => {
      const [startH, startM] = item.start_time.split(':').map(Number);
      const [endH, endM] = item.end_time.split(':').map(Number);

      const startDate = new Date();
      startDate.setHours(startH, startM, 0, 0);

      const endDate = new Date();
      endDate.setHours(endH, endM, 0, 0);

      const diffStart = startDate.getTime() - now.getTime();
      const diffEnd = endDate.getTime() - now.getTime();

      // Schedule Start
      if (diffStart > 0) {
        const id = window.setTimeout(() => {
          if (item.type === 'study') {
            this.notify(`Module ${item.module || ''} Study Session Started`, `Time to focus on: ${item.title}`, 'start');
          } else if (item.type === 'break' || item.type === 'lunch') {
            this.notify(`Time for a ${item.duration_minutes}-minute break!`, 'Take some rest and recharge.', 'break');
          } else if (item.type === 'revision') {
            this.notify(`Revision Session Started`, `Reviewing: ${item.title}`, 'start');
          }
        }, diffStart);
        this.activeTimeouts.push(id);
      }

      // Schedule End
      if (diffEnd > 0) {
        const id = window.setTimeout(() => {
          if (item.type === 'study') {
            this.notify(`Module ${item.module || ''} Session Ended`, 'Well done! Wrap up your thoughts.', 'end');
          } else if (item.type === 'break' || item.type === 'lunch') {
            this.notify(`Break is over`, "Let's get back to studying!", 'end');
          }
        }, diffEnd);
        this.activeTimeouts.push(id);
      }
    });
  }
}

export const reminderService = new ReminderService();
