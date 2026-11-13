import React, { useState, useEffect } from 'react';
import { TimetableDay, TimetableItem } from '../types/api';
import { reminderService, SimulationState } from '../services/reminders';
import { Clock, ArrowRight, Bell, BellOff, Check, Volume2, VolumeX, Play } from 'lucide-react';

interface Props {
  currentDay: TimetableDay;
  planId?: string;
}

export const ActiveStatusBar: React.FC<Props> = ({ currentDay, planId = 'active_plan' }) => {
  const [nowTime, setNowTime] = useState<Date>(new Date());
  const [activeItem, setActiveItem] = useState<TimetableItem | null>(null);
  const [nextItem, setNextItem] = useState<TimetableItem | null>(null);
  const [permission, setPermission] = useState<NotificationPermission>(reminderService.getPermission());
  const [testSent, setTestSent] = useState<boolean>(false);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(reminderService.isSoundEnabled());
  const [simState, setSimState] = useState<SimulationState | null>(null);

  // Keep clock fresh for status badges
  useEffect(() => {
    const timer = setInterval(() => setNowTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Schedule timetable items whenever currentDay or planId changes
  useEffect(() => {
    if (currentDay && currentDay.items && currentDay.items.length > 0) {
      reminderService.scheduleDayItems(currentDay.items, planId, currentDay.day_number);
    }
  }, [currentDay, planId]);

  // Determine active item and next up item
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
      reminderService.scheduleDayItems(currentDay.items, planId, currentDay.day_number);
      reminderService.notify(
        'Reminders Enabled',
        'You will receive study & break notifications for this timetable.',
        'test'
      );
    }
  };

  const handleSendTest = () => {
    reminderService.notify(
      'Test Reminder: Break Time',
      'Time for a 15-minute break. Take some rest!',
      'break'
    );
    setTestSent(true);
    setTimeout(() => setTestSent(false), 3000);
  };

  const handleToggleSound = () => {
    const nextVal = !soundEnabled;
    reminderService.setSoundEnabled(nextVal);
    setSoundEnabled(nextVal);
  };

  const handleSimulate = () => {
    if (simState?.isRunning) return;
    const cancelSim = reminderService.simulateSession(
      activeItem?.module || 1,
      5,
      5,
      (state) => {
        setSimState(state);
        if (!state.isRunning) {
          setTimeout(() => setSimState(null), 3000);
        }
      }
    );
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 sm:p-4 mb-6 shadow-xs">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
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
        <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto shrink-0">
          {/* Permission status button */}
          {permission === 'granted' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200">
              <Bell className="w-3.5 h-3.5" />
              Reminders Active
            </span>
          ) : permission === 'denied' ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200">
              <BellOff className="w-3.5 h-3.5" />
              Notifications Blocked (In-App Only)
            </span>
          ) : (
            <button
              onClick={handleEnableReminders}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors shadow-xs"
            >
              <Bell className="w-3.5 h-3.5" />
              Enable Reminders
            </button>
          )}

          {/* Sound Alerts Toggle */}
          <button
            onClick={handleToggleSound}
            title={soundEnabled ? 'Disable soft chime alert' : 'Enable soft chime alert'}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-medium transition-colors ${
              soundEnabled
                ? 'border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                : 'border-slate-300 hover:bg-slate-50 text-slate-600'
            }`}
          >
            {soundEnabled ? (
              <Volume2 className="w-3.5 h-3.5 text-indigo-600" />
            ) : (
              <VolumeX className="w-3.5 h-3.5 text-slate-400" />
            )}
            <span>Sound alerts {soundEnabled ? 'ON' : 'OFF'}</span>
          </button>

          {/* Test Reminder */}
          <button
            onClick={handleSendTest}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
          >
            {testSent ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Clock className="w-3.5 h-3.5" />}
            {testSent ? 'Sent!' : 'Send test reminder'}
          </button>

          {/* Simulation Helper */}
          <button
            onClick={handleSimulate}
            disabled={simState?.isRunning}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-medium transition-colors ${
              simState?.isRunning
                ? 'border-amber-300 bg-amber-50 text-amber-800 animate-pulse'
                : 'border-slate-300 hover:bg-slate-50 text-slate-700'
            }`}
            title="Fast 10s demo: 5s Study Session -> 5s Break Session"
          >
            <Play className="w-3.5 h-3.5 text-indigo-600" />
            {simState?.isRunning
              ? simState.step === 'study'
                ? `Simulating Study (${simState.secondsLeft}s)`
                : `Simulating Break (${simState.secondsLeft}s)`
              : 'Simulate 5s session'}
          </button>
        </div>
      </div>

      {/* Disclaimers & Timezone */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-slate-400 mt-2.5 pt-2 border-t border-slate-100">
        <p>
          Reminders work while this site is open in your browser (background tabs supported). On iOS, add site to Home Screen.
        </p>
        <span className="shrink-0 text-slate-400">
          Timezone: {reminderService.getLocalTimeZone()} ({reminderService.getTimezoneOffsetString()})
        </span>
      </div>
    </div>
  );
};
