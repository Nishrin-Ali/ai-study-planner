import React, { useState, useEffect } from 'react';
import { TimetableDay, TimetableItem } from '../types/api';
import { reminderService } from '../services/reminders';
import { Clock, ArrowRight, Bell, BellOff, Check } from 'lucide-react';

interface Props {
  currentDay: TimetableDay;
}

export const ActiveStatusBar: React.FC<Props> = ({ currentDay }) => {
  const [nowTime, setNowTime] = useState<Date>(new Date());
  const [activeItem, setActiveItem] = useState<TimetableItem | null>(null);
  const [nextItem, setNextItem] = useState<TimetableItem | null>(null);
  const [permission, setPermission] = useState<NotificationPermission>(reminderService.getPermission());
  const [testSent, setTestSent] = useState<boolean>(false);

  useEffect(() => {
    const timer = setInterval(() => setNowTime(new Date()), 10000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!currentDay || !currentDay.items) return;

    const currentMinutes = nowTime.getHours() * 60 + nowTime.getMinutes();
    let current: TimetableItem | null = null;
    let next: TimetableItem | null = null;

    for (let i = 0; i < currentDay.items.length; i++) {
      const it = currentDay.items[i];
      const [sh, sm] = it.start_time.split(':').map(Number);
      const [eh, em] = it.end_time.split(':').map(Number);
      const startMin = sh * 60 + sm;
      const endMin = eh * 60 + em;

      if (currentMinutes >= startMin && currentMinutes < endMin) {
        current = it;
        next = currentDay.items[i + 1] || null;
        break;
      } else if (currentMinutes < startMin) {
        if (!next) next = it;
      }
    }

    setActiveItem(current);
    setNextItem(next);
  }, [currentDay, nowTime]);

  const handleEnableReminders = async () => {
    const res = await reminderService.requestPermission();
    setPermission(res);
    if (res === 'granted' && currentDay) {
      reminderService.scheduleDayItems(currentDay.items);
      reminderService.notify('Reminders Enabled', 'You will receive study & break notifications for this timetable.', 'test');
    }
  };

  const handleSendTest = () => {
    reminderService.notify('Test Reminder: Break Time', 'Time for a 15-minute break. Stretch and hydrate!', 'break');
    setTestSent(true);
    setTimeout(() => setTestSent(false), 3000);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 sm:p-4 mb-6 shadow-xs">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Now & Next status */}
        <div className="flex flex-wrap items-center gap-4 sm:gap-6 text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-slate-500 font-medium">Now:</span>
            <span className="font-semibold text-slate-900 truncate max-w-[200px] sm:max-w-[280px]">
              {activeItem ? activeItem.title : 'No active session (Off schedule)'}
            </span>
          </div>

          <div className="flex items-center gap-2 border-l border-slate-200 pl-4 sm:pl-6">
            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Next:</span>
            <span className="text-slate-700 truncate max-w-[200px]">
              {nextItem ? `${nextItem.title} (${nextItem.start_time})` : 'End of day'}
            </span>
          </div>
        </div>

        {/* Reminder Controls */}
        <div className="flex items-center gap-2 self-start md:self-auto shrink-0">
          {permission === 'granted' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200">
              <Bell className="w-3.5 h-3.5" />
              Reminders Active
            </span>
          ) : permission === 'denied' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200">
              <BellOff className="w-3.5 h-3.5" />
              Notifications Blocked (In-App Only)
            </span>
          ) : (
            <button
              onClick={handleEnableReminders}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors"
            >
              <Bell className="w-3.5 h-3.5" />
              Enable Reminders
            </button>
          )}

          <button
            onClick={handleSendTest}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
          >
            {testSent ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Clock className="w-3.5 h-3.5" />}
            {testSent ? 'Sent!' : 'Test Reminder'}
          </button>
        </div>
      </div>

      <p className="text-[11px] text-slate-400 mt-2">
        Reminders work while this site is open in your browser (background tabs supported).
      </p>
    </div>
  );
};
