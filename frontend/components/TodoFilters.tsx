import React, { useMemo } from 'react';
import { useTodo } from '../contexts/TodoContext';
import { motion } from 'framer-motion';

const TodoFilters: React.FC = () => {
  const { state, setFilter, setSortBy, setSortOrder, setPriorityFilter, setTagFilter } = useTodo();

  const statusFilters = [
    { id: 'all', label: 'All' },
    { id: 'active', label: 'Active' },
    { id: 'completed', label: 'Completed' },
  ];

  const priorityFilters = [
    { id: 'all', label: 'All' },
    { id: 'high', label: 'High', color: 'bg-orange text-navy-blue' },
    { id: 'medium', label: 'Medium', color: 'bg-peach text-navy-blue' },
    { id: 'low', label: 'Low', color: 'bg-navy-blue text-white' },
  ];

  const sortOptions = [
    { id: 'manual', label: 'Manual' },
    { id: 'priority', label: 'Priority' },
    { id: 'dueDate', label: 'Due Date' },
    { id: 'name', label: 'Name' },
    { id: 'createdAt', label: 'Created' },
  ];

  // Compute unique tags from all todos
  const uniqueTags = useMemo(() => {
    const tagSet = new Set<string>();
    state.todos.forEach(todo => {
      (todo.tags || []).forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [state.todos]);

  return (
    <div className="space-y-3 mb-6">
      {/* Status filter row */}
      <div className="flex space-x-2">
        {statusFilters.map((filter) => (
          <motion.button
            key={filter.id}
            onClick={() => setFilter(filter.id as 'all' | 'active' | 'completed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              state.filter === filter.id
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {filter.label}
          </motion.button>
        ))}
      </div>

      {/* Priority filter row */}
      <div className="flex items-center space-x-2">
        <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">Priority:</span>
        {priorityFilters.map((pf) => (
          <motion.button
            key={pf.id}
            onClick={() => setPriorityFilter(pf.id as 'all' | 'low' | 'medium' | 'high')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              state.priorityFilter === pf.id
                ? (pf.color || 'bg-blue-500 text-white') + ' shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {pf.label}
          </motion.button>
        ))}
      </div>

      {/* Sort + tag filter row */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">Sort:</span>
          <select
            value={state.sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-orange"
          >
            {sortOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>
          <motion.button
            onClick={() => setSortOrder(state.sortOrder === 'asc' ? 'desc' : 'asc')}
            className="px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title={state.sortOrder === 'asc' ? 'Ascending' : 'Descending'}
          >
            {state.sortOrder === 'asc' ? '\u2191 Asc' : '\u2193 Desc'}
          </motion.button>
        </div>

        {uniqueTags.length > 0 && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">Tag:</span>
            <select
              value={state.tagFilter || ''}
              onChange={(e) => setTagFilter(e.target.value || null)}
              className="px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-orange"
            >
              <option value="">All Tags</option>
              {uniqueTags.map((tag) => (
                <option key={tag} value={tag}>#{tag}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
};

export default TodoFilters;
