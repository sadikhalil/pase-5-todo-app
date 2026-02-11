import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const EVENT_CONFIG = {
  'task.created': { label: 'Task Created', color: 'bg-green-500', icon: '+' },
  'task.updated': { label: 'Task Updated', color: 'bg-blue-500', icon: '~' },
  'task.completed': { label: 'Task Completed', color: 'bg-purple-500', icon: '✓' },
  'task.deleted': { label: 'Task Deleted', color: 'bg-red-500', icon: '×' },
};

const EventToast = ({ toasts = [], onDismiss }) => {
  return (
    <div className="fixed top-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => {
          const config = EVENT_CONFIG[toast.event_type] || {
            label: 'Event',
            color: 'bg-gray-500',
            icon: '?',
          };
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 100 }}
              className="pointer-events-auto flex items-center gap-3 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 px-4 py-3 min-w-[280px]"
            >
              <div
                className={`w-8 h-8 ${config.color} text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0`}
              >
                {config.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-gray-900 dark:text-white">
                  {config.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {toast.title || `Task #${toast.task_id}`}
                </div>
              </div>
              <button
                onClick={() => onDismiss(toast.id)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm flex-shrink-0"
              >
                ✕
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

/**
 * Hook to manage toast notifications from SSE events.
 * Returns [toasts, addToast, dismissToast].
 */
export function useEventToasts(autoDissmissMs = 5000) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((event) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const toast = { ...event, id };
    setToasts((prev) => [...prev, toast]);

    // Auto-dismiss
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, autoDissmissMs);
  }, [autoDissmissMs]);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return [toasts, addToast, dismissToast];
}

export default EventToast;
