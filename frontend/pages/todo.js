import React, { useEffect } from 'react';
import { TodoProvider, useTodo } from '../contexts/TodoContext';
import TodoInput from '../components/TodoInput';
import TodoFilters from '../components/TodoFilters';
import SortableTodoList from '../components/SortableTodoList';
import ProgressBar from '../components/ProgressBar';
import Layout from '../components/Layout';
import { Toaster } from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import EventToast, { useEventToasts } from '../components/EventToast';
import apiClient from '../lib/apiClient';

const ClearCompletedSection = () => {
  const { state, clearCompleted } = useTodo();
  const completedCount = state.todos.filter(t => t.status === 'complete').length;

  if (completedCount === 0) return null;

  return (
    <button
      onClick={clearCompleted}
      className="text-sm text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
    >
      Clear Completed ({completedCount})
    </button>
  );
};

const TodoPageContent = () => {
  const { user } = useAuth();
  const { refreshTodos } = useTodo();
  const [toasts, addToast, dismissToast] = useEventToasts();

  // SSE connection for real-time events
  useEffect(() => {
    if (!user?.id) return;

    const eventSource = apiClient.connectEventStream(user.id, (event) => {
      addToast(event);
      // Auto-refresh todos on any event
      refreshTodos();
    });

    return () => {
      eventSource.close();
    };
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Layout title="Modern Todo App" description="A modern, interactive todo application">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Hello, {user?.email?.split('@')[0]}! 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          What would you like to accomplish today?
        </p>
      </div>

      <TodoInput />

      <div className="mt-8 w-full max-w-2xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Your Tasks</h2>
          <div className="flex items-center gap-4">
            <ClearCompletedSection />
            <ProgressBar />
          </div>
        </div>

        <TodoFilters />

        <div className="mt-4">
          <SortableTodoList />
        </div>
      </div>

      {/* SSE Event Toasts */}
      <EventToast toasts={toasts} onDismiss={dismissToast} />

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
    </Layout>
  );
};

const TodoPage = () => {
  return (
    <TodoProvider>
      <TodoPageContent />
    </TodoProvider>
  );
};

export default TodoPage;
