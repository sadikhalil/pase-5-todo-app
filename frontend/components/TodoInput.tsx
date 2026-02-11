import React, { useState } from 'react';
import { useTodo } from '../contexts/TodoContext';
import { motion } from 'framer-motion';
import Button from './ui/Button';

interface TodoInputProps {
  placeholder?: string;
}

const TodoInput: React.FC<TodoInputProps> = ({ placeholder = 'Add a new task...' }) => {
  const [inputValue, setInputValue] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState<string>('');
  const [reminderDate, setReminderDate] = useState<string>('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [recurrence, setRecurrence] = useState('none');
  const [isExpanded, setIsExpanded] = useState(false);
  const { addTodo } = useTodo();

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      const newTag = tagInput.trim().toLowerCase();
      if (!tags.includes(newTag)) {
        setTags([...tags, newTag]);
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      // Create the task with all fields
      addTodo(
        inputValue.trim(),
        description.trim() || undefined,
        dueDate ? new Date(dueDate) : undefined,
        reminderDate ? new Date(reminderDate) : undefined,
        priority,
        tags.length > 0 ? tags : undefined,
        recurrence !== 'none' ? recurrence : undefined,
      );

      // Reset form
      setInputValue('');
      setDescription('');
      setDueDate('');
      setReminderDate('');
      setPriority('medium');
      setTags([]);
      setTagInput('');
      setRecurrence('none');
      setIsExpanded(false);
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="space-y-3">
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={placeholder}
              className="w-full px-5 py-4 bg-white text-navy-blue rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent shadow-sm"
              aria-label="Add a new task"
            />
          </div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button type="submit" disabled={!inputValue.trim()}>
              Add Task
            </Button>
          </motion.div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
          >
            {isExpanded ? 'Hide Details' : 'Add Details'}
          </button>
        </div>

        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 bg-white dark:bg-peach text-navy-blue dark:text-navy-blue rounded-lg space-y-3"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Add details about this task..."
                  className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent resize-none"
                  rows={2}
                />
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                    Priority
                  </label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
                    className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                    Reminder
                  </label>
                  <input
                    type="datetime-local"
                    value={reminderDate}
                    onChange={(e) => setReminderDate(e.target.value)}
                    className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                    Recurrence
                  </label>
                  <select
                    value={recurrence}
                    onChange={(e) => setRecurrence(e.target.value)}
                    className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent"
                  >
                    <option value="none">None</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-navy-blue dark:text-navy-blue mb-1">
                Tags
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-md text-xs"
                  >
                    #{tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="text-blue-500 hover:text-blue-700 font-bold"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleAddTag}
                placeholder="Type a tag and press Enter..."
                className="w-full px-3 py-2 bg-white text-navy-blue rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-orange focus:border-transparent"
              />
            </div>
          </motion.div>
        )}
      </div>
    </motion.form>
  );
};

export default TodoInput;