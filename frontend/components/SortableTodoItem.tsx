import React, { useState, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion } from 'framer-motion';
import { Trash2, CheckCircle, Circle, GripVertical, X } from 'lucide-react';
import { Todo } from '../types/todo';
import ConfettiEffect from './ConfettiEffect';
import Button from './ui/Button';

interface SortableTodoItemProps {
  todo: Todo;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (id: string, text: string, description?: string, dueDate?: Date, reminderDate?: Date, priority?: 'low' | 'medium' | 'high', tags?: string[], recurrence?: string) => void;
}

const SortableTodoItem: React.FC<SortableTodoItemProps> = ({ todo, onToggle, onDelete, onEdit }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: todo.id });

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(todo.text);
  const [editDescription, setEditDescription] = useState(todo.description || '');
  const [editDueDate, setEditDueDate] = useState(todo.dueDate ? new Date(todo.dueDate).toISOString().split('T')[0] : '');
  const [editReminderDate, setEditReminderDate] = useState(todo.reminderDate ? new Date(todo.reminderDate).toISOString().slice(0, 16) : '');
  const [editPriority, setEditPriority] = useState<'low' | 'medium' | 'high'>(todo.priority || 'medium');
  const [editTags, setEditTags] = useState<string[]>(todo.tags || []);
  const [editTagInput, setEditTagInput] = useState('');
  const [editRecurrence, setEditRecurrence] = useState(todo.recurrence || 'none');
  const [showConfetti, setShowConfetti] = useState(false);
  const [wasIncomplete, setWasIncomplete] = useState(todo.status !== 'complete');

  useEffect(() => {
    // Show confetti when a task is completed (but not when it becomes incomplete again)
    if (todo.status === 'complete' && wasIncomplete) {
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 2000); // Hide confetti after 2 seconds
      setWasIncomplete(false);
    } else if (todo.status !== 'complete') {
      setWasIncomplete(true);
    }
  }, [todo.status, wasIncomplete]);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 1,
  };

  const handleEdit = () => {
    setIsEditing(!isEditing);
  };

  const handleCancelEdit = () => {
    setEditText(todo.text);
    setEditDescription(todo.description || '');
    setEditDueDate(todo.dueDate ? new Date(todo.dueDate).toISOString().split('T')[0] : '');
    setEditReminderDate(todo.reminderDate ? new Date(todo.reminderDate).toISOString().slice(0, 16) : '');
    setEditPriority(todo.priority || 'medium');
    setEditTags(todo.tags || []);
    setEditTagInput('');
    setEditRecurrence(todo.recurrence || 'none');
    setIsEditing(false);
  };

  const handleAddEditTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && editTagInput.trim()) {
      e.preventDefault();
      const newTag = editTagInput.trim().toLowerCase();
      if (!editTags.includes(newTag)) {
        setEditTags([...editTags, newTag]);
      }
      setEditTagInput('');
    }
  };

  const handleRemoveEditTag = (tagToRemove: string) => {
    setEditTags(editTags.filter(t => t !== tagToRemove));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onEdit(
      todo.id,
      editText,
      editDescription || undefined,
      editDueDate ? new Date(editDueDate) : undefined,
      editReminderDate ? new Date(editReminderDate) : undefined,
      editPriority,
      editTags,
      editRecurrence,
    );
    setIsEditing(false);
  };

  return (
    <>
      {showConfetti && <ConfettiEffect isActive={true} />}
      <motion.div
        ref={setNodeRef}
        style={style}
        layout
        initial={{ opacity: 0, x: 100, scale: 0.8 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: -100, height: 0, scale: 0.8 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-start space-x-3 flex-1 min-w-0">
          <motion.button
            {...attributes}
            {...listeners}
            className="flex-shrink-0 cursor-grab active:cursor-grabbing mt-1"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            aria-label="Drag to reorder"
          >
            <GripVertical className="text-gray-400" size={20} />
          </motion.button>

          <motion.button
            onClick={() => onToggle(todo.id)}
            className="flex-shrink-0 mt-1"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            aria-label={todo.status === 'complete' ? "Mark as incomplete" : "Mark as complete"}
          >
            {todo.status === 'complete' ? (
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: 180 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <CheckCircle className="text-green-500" size={24} />
              </motion.div>
            ) : (
              <motion.div
                initial={{ scale: 0, rotate: 180 }}
                animate={{ scale: 1, rotate: 0 }}
                exit={{ scale: 0, rotate: -180 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <Circle className="text-gray-400" size={24} />
              </motion.div>
            )}
          </motion.button>

          {isEditing ? (
            <form onSubmit={handleSubmit} className="flex-1 min-w-0 space-y-3">
              <div className="space-y-3">
                <input
                  type="text"
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue pb-2 text-lg font-medium"
                  autoFocus
                />

                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Add description..."
                  className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue pb-2 text-sm"
                  rows={2}
                />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Priority</label>
                    <select
                      value={editPriority}
                      onChange={(e) => setEditPriority(e.target.value as 'low' | 'medium' | 'high')}
                      className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue text-sm"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Due Date</label>
                    <input
                      type="date"
                      value={editDueDate}
                      onChange={(e) => setEditDueDate(e.target.value)}
                      className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Reminder</label>
                    <input
                      type="datetime-local"
                      value={editReminderDate}
                      onChange={(e) => setEditReminderDate(e.target.value)}
                      className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue text-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Recurrence</label>
                    <select
                      value={editRecurrence}
                      onChange={(e) => setEditRecurrence(e.target.value)}
                      className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue text-sm"
                    >
                      <option value="none">None</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Tags</label>
                    <div className="flex flex-wrap gap-1 mb-1">
                      {editTags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded text-xs"
                        >
                          #{tag}
                          <button
                            type="button"
                            onClick={() => handleRemoveEditTag(tag)}
                            className="text-blue-500 hover:text-blue-700"
                          >
                            <X size={12} />
                          </button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      value={editTagInput}
                      onChange={(e) => setEditTagInput(e.target.value)}
                      onKeyDown={handleAddEditTag}
                      placeholder="Type tag + Enter"
                      className="w-full bg-transparent border-b border-orange focus:outline-none focus:border-navy-blue text-sm"
                    />
                  </div>
                </div>
              </div>

              <div className="flex space-x-2 mt-3">
                <Button size="sm" type="submit">Save</Button>
                <Button size="sm" variant="ghost" onClick={handleCancelEdit}>Cancel</Button>
              </div>
            </form>
          ) : (
            <div className="flex-1 min-w-0">
              <motion.div
                className={`font-medium ${todo.status === 'complete' ? 'line-through text-gray-500 dark:text-gray-500' : 'text-navy-blue dark:text-white'}`}
                animate={{
                  textDecoration: todo.status === 'complete' ? 'line-through' : 'none',
                  color: todo.status === 'complete' ? '#9CA3AF' : '#1F2937'
                }}
                transition={{ duration: 0.3 }}
              >
                {todo.text}
              </motion.div>

              {todo.description && (
                <div className="text-sm text-navy-blue dark:text-gray-300 mt-1">
                  {todo.description}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 mt-2">
                {todo.priority && (
                  <div className={`text-xs px-2 py-1 rounded-md ${
                    todo.priority === 'high' ? 'bg-orange text-navy-blue' :
                    todo.priority === 'medium' ? 'bg-peach text-navy-blue' :
                    'bg-navy-blue text-white'
                  }`}>
                    {todo.priority} priority
                  </div>
                )}

                {todo.dueDate && (
                  <div className="flex items-center text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-navy-blue dark:text-gray-300">
                    <span className="mr-1">📅</span>
                    {new Date(todo.dueDate).toLocaleDateString()}
                  </div>
                )}

                {todo.recurrence && todo.recurrence !== 'none' && (
                  <div className="flex items-center text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-navy-blue dark:text-gray-300">
                    <span className="mr-1">🔁</span>
                    {todo.recurrence}
                  </div>
                )}

                {todo.tags && todo.tags.length > 0 && todo.tags.map((tag, index) => (
                  <div
                    key={index}
                    className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 rounded-md text-blue-700 dark:text-blue-300"
                  >
                    #{tag}
                  </div>
                ))}

                {todo.createdAt && (
                  <div className="text-xs text-gray-400 dark:text-gray-500">
                    Created {new Date(todo.createdAt).toLocaleDateString()}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end mt-2">
          <div className="flex items-center space-x-2">
            {!isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleEdit}
                aria-label="Edit task"
              >
                Edit
              </Button>
            )}
            <motion.button
              onClick={() => onDelete(todo.id)}
              className="p-2 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              aria-label="Delete task"
            >
              <Trash2 size={18} />
            </motion.button>
          </div>
        </div>
      </motion.div>
    </>
  );
};

export default SortableTodoItem;
