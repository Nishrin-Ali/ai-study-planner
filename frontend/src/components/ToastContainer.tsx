import React, { useState, useEffect } from 'react';
import { reminderService } from '../services/reminders';
import { CheckCircle2, Clock, BellRing, X } from 'lucide-react';

interface Toast {
  id: string;
  title: string;
  body: string;
  type: string;
}

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const unsubscribe = reminderService.subscribe((notification) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, ...notification }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 6000);
    });

    return () => unsubscribe();
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="pointer-events-auto bg-white border border-slate-200 rounded-lg p-4 shadow-md flex items-start gap-3 transition-all animate-in fade-in slide-in-from-bottom-2"
        >
          {toast.type === 'break' ? (
            <Clock className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
          ) : toast.type === 'end' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5 shrink-0" />
          ) : (
            <BellRing className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-slate-900">{toast.title}</h4>
            <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{toast.body}</p>
          </div>
          <button
            onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
            className="text-slate-400 hover:text-slate-600 p-0.5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};
