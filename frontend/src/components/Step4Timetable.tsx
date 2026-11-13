import React, { useState } from 'react';
import { StudyPlanResponse, TimetableDay, TimetableItem } from '../types/api';
import { togglePlanItemCompletion } from '../services/api';
import { ActiveStatusBar } from './ActiveStatusBar';
import {
  Clock,
  BookOpen,
  Coffee,
  RotateCcw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ExternalLink,
  PlusCircle,
} from 'lucide-react';

interface Props {
  plan: StudyPlanResponse;
  onReset: () => void;
}

export const Step4Timetable: React.FC<Props> = ({ plan, onReset }) => {
  const [selectedDayIdx, setSelectedDayIdx] = useState(0);
  const [expandedAnswerId, setExpandedAnswerId] = useState<string | null>(null);
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>(() => {
    const map: Record<string, boolean> = {};
    plan.days.forEach((d) => {
      d.items.forEach((it) => {
        if (it.is_completed) map[it.id] = true;
      });
    });
    return map;
  });

  const activeDay: TimetableDay = plan.days[selectedDayIdx] || plan.days[0];

  const handleToggleComplete = async (itemId: string, currentVal: boolean) => {
    const newVal = !currentVal;
    setCompletedItems((prev) => ({ ...prev, [itemId]: newVal }));
    try {
      await togglePlanItemCompletion(plan.plan_id, itemId, newVal);
    } catch (e) {
      // Keep optimistic UI state
    }
  };

  const getItemBadge = (item: TimetableItem) => {
    switch (item.type) {
      case 'break':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <Coffee className="w-3 h-3" /> Break
          </span>
        );
      case 'lunch':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-orange-50 text-orange-700 border border-orange-200">
            <Coffee className="w-3 h-3" /> Lunch
          </span>
        );
      case 'revision':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
            <RotateCcw className="w-3 h-3" /> Revision
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
            <BookOpen className="w-3 h-3" /> Module {item.module || ''}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Sticky Top Status & Reminder Controls */}
      <ActiveStatusBar currentDay={activeDay} />

      {/* Plan Header & Meta */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-900 tracking-tight">
              {plan.course_code}: {plan.course_title}
            </h2>
            <span className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
              {plan.num_modules} Modules • {plan.num_days} Days
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic timetable generated from VTU syllabus requirements.
          </p>
        </div>

        <button
          onClick={onReset}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shrink-0 self-start sm:self-auto"
        >
          <PlusCircle className="w-3.5 h-3.5 text-slate-500" />
          <span>Create New Plan</span>
        </button>
      </div>

      {/* Heavy Plan Warning */}
      {plan.is_heavy_plan && plan.heavy_warning && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-semibold text-amber-900">Heavy Workload Advisory</h4>
            <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">{plan.heavy_warning}</p>
          </div>
        </div>
      )}

      {/* Day Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto gap-1">
        {plan.days.map((day, idx) => (
          <button
            key={day.day_number}
            onClick={() => setSelectedDayIdx(idx)}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
              selectedDayIdx === idx
                ? 'border-indigo-600 text-indigo-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {day.date_label}
            <span className="ml-1.5 text-[10px] text-slate-400">
              ({Math.round(day.total_study_minutes / 60)}h)
            </span>
          </button>
        ))}
      </div>

      {/* Day Schedule List */}
      <div className="space-y-3">
        {activeDay.items.map((item) => {
          const isDone = completedItems[item.id] || false;
          const answer = item.answer_id ? plan.answers[item.answer_id] : null;
          const isExpanded = expandedAnswerId === item.answer_id;

          return (
            <div
              key={item.id}
              className={`bg-white border rounded-lg transition-all ${
                isDone
                  ? 'border-slate-200 bg-slate-50/50 opacity-75'
                  : 'border-slate-200 shadow-xs hover:border-slate-300'
              }`}
            >
              <div className="p-4 flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  {/* Completion Checkbox (study/revision items) */}
                  {item.type === 'study' || item.type === 'revision' ? (
                    <button
                      type="button"
                      onClick={() => handleToggleComplete(item.id, isDone)}
                      className={`mt-0.5 h-4 w-4 rounded border flex items-center justify-center transition-colors ${
                        isDone
                          ? 'bg-indigo-600 border-indigo-600 text-white'
                          : 'border-slate-300 hover:border-indigo-500'
                      }`}
                    >
                      {isDone && <CheckCircle2 className="w-3.5 h-3.5" />}
                    </button>
                  ) : (
                    <div className="w-4" />
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      {getItemBadge(item)}
                      <span className="text-xs font-mono text-slate-500">
                        {item.start_time} – {item.end_time} ({item.duration_minutes}m)
                      </span>
                    </div>

                    <h3
                      className={`text-xs sm:text-sm font-semibold tracking-tight text-slate-900 ${
                        isDone ? 'line-through text-slate-400' : ''
                      }`}
                    >
                      {item.title}
                    </h3>
                  </div>
                </div>

                {/* View Answer button */}
                {answer && (
                  <button
                    type="button"
                    onClick={() =>
                      setExpandedAnswerId(isExpanded ? null : (item.answer_id as string))
                    }
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors shrink-0"
                  >
                    <span>{isExpanded ? 'Hide Answer' : 'View Answer'}</span>
                    {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                )}
              </div>

              {/* Expandable Answer Card */}
              {answer && isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-slate-100 bg-slate-50/50 text-xs">
                  <div className="mb-2">
                    <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-500">
                      Grounded Answer & Key Points:
                    </span>
                  </div>
                  <div className="text-slate-700 leading-relaxed whitespace-pre-line bg-white p-3 rounded border border-slate-200">
                    {answer.content}
                  </div>

                  {/* Attribution Source */}
                  <div className="mt-2.5 flex flex-wrap items-center justify-between text-[11px] text-slate-500 gap-2">
                    <span>
                      <strong className="text-slate-600">Source:</strong> {answer.source_attribution}
                    </span>
                    {answer.source_urls && answer.source_urls.length > 0 && (
                      <div className="flex items-center gap-2">
                        {answer.source_urls.map((url, i) => (
                          <a
                            key={i}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
                          >
                            <span>Link {i + 1}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
