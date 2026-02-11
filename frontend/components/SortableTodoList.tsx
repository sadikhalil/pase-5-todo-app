import React, { useMemo } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useTodo } from '../contexts/TodoContext';
import SortableTodoItem from './SortableTodoItem';
import { AnimatePresence } from 'framer-motion';
import { Todo } from '../types/todo';

const PRIORITY_VALUE: Record<string, number> = { high: 3, medium: 2, low: 1 };

const SortableTodoList: React.FC = () => {
  const { state, toggleTodo, deleteTodo, updateTodo, reorderTodos } = useTodo();

  const isManualSort = state.sortBy === 'manual';

  // Multi-stage filter + sort pipeline
  const processedTodos = useMemo(() => {
    let result = [...state.todos];

    // Stage 1: Status filter
    if (state.filter === 'active') {
      result = result.filter(todo => todo.status !== 'complete');
    } else if (state.filter === 'completed') {
      result = result.filter(todo => todo.status === 'complete');
    }

    // Stage 2: Priority filter
    if (state.priorityFilter !== 'all') {
      result = result.filter(todo => todo.priority === state.priorityFilter);
    }

    // Stage 3: Tag filter
    if (state.tagFilter) {
      result = result.filter(todo =>
        (todo.tags || []).includes(state.tagFilter!)
      );
    }

    // Stage 4: Sort (only when not manual)
    if (!isManualSort) {
      const multiplier = state.sortOrder === 'asc' ? 1 : -1;
      result.sort((a: Todo, b: Todo) => {
        switch (state.sortBy) {
          case 'priority': {
            const aVal = PRIORITY_VALUE[a.priority || 'medium'] || 2;
            const bVal = PRIORITY_VALUE[b.priority || 'medium'] || 2;
            return (aVal - bVal) * multiplier;
          }
          case 'dueDate': {
            const aDate = a.dueDate ? new Date(a.dueDate).getTime() : Infinity;
            const bDate = b.dueDate ? new Date(b.dueDate).getTime() : Infinity;
            return (aDate - bDate) * multiplier;
          }
          case 'name':
            return a.text.localeCompare(b.text) * multiplier;
          case 'createdAt': {
            const aTime = new Date(a.createdAt).getTime();
            const bTime = new Date(b.createdAt).getTime();
            return (aTime - bTime) * multiplier;
          }
          default:
            return 0;
        }
      });
    }

    return result;
  }, [state.todos, state.filter, state.priorityFilter, state.tagFilter, state.sortBy, state.sortOrder, isManualSort]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    if (!isManualSort) return; // Ignore drag when sort is active

    const { active, over } = event;

    if (over && active.id !== over.id) {
      const activeIndex = processedTodos.findIndex(todo => todo.id === active.id);
      const overIndex = processedTodos.findIndex(todo => todo.id === over.id);

      if (activeIndex !== -1 && overIndex !== -1) {
        reorderTodos(String(active.id), String(over.id));
      }
    }
  };

  // Build empty state message based on active filters
  const getEmptyMessage = () => {
    const hasFilters = state.priorityFilter !== 'all' || state.tagFilter;
    if (hasFilters) {
      return 'No tasks match the current filters';
    }
    if (state.filter === 'completed') return 'No completed tasks yet';
    if (state.filter === 'active') return 'No active tasks';
    return 'Add your first task to get started!';
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <div className="w-full max-w-2xl">
        <SortableContext
          items={processedTodos.map(todo => todo.id)}
          strategy={verticalListSortingStrategy}
          disabled={!isManualSort}
        >
          <AnimatePresence>
            {processedTodos.length > 0 ? (
              <ul className="space-y-3">
                {processedTodos.map(todo => (
                  <SortableTodoItem
                    key={todo.id}
                    todo={todo}
                    onToggle={toggleTodo}
                    onDelete={deleteTodo}
                    onEdit={updateTodo}
                  />
                ))}
              </ul>
            ) : (
              <div className="text-center py-12">
                <div className="text-gray-500 dark:text-gray-400 text-lg">
                  {getEmptyMessage()}
                </div>
              </div>
            )}
          </AnimatePresence>
        </SortableContext>
      </div>
    </DndContext>
  );
};

export default SortableTodoList;
