import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { Todo } from '../types/todo';
import { showToast } from '../components/Toast';
import { useAuth } from './AuthContext'; // Import AuthContext to get the token
import apiClient from '../lib/apiClient';

interface TodoState {
  todos: Todo[];
  filter: 'all' | 'active' | 'completed';
  sortBy: 'manual' | 'priority' | 'dueDate' | 'name' | 'createdAt';
  sortOrder: 'asc' | 'desc';
  priorityFilter: 'all' | 'low' | 'medium' | 'high';
  tagFilter: string | null;
}

interface TodoContextType {
  state: TodoState;
  addTodo: (text: string, description?: string, dueDate?: Date, reminderDate?: Date, priority?: 'low' | 'medium' | 'high', tags?: string[], recurrence?: string) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
  updateTodo: (id: string, text: string, description?: string, dueDate?: Date, reminderDate?: Date, priority?: 'low' | 'medium' | 'high', tags?: string[], recurrence?: string) => void;
  clearCompleted: () => void;
  setFilter: (filter: 'all' | 'active' | 'completed') => void;
  setSortBy: (sortBy: 'manual' | 'priority' | 'dueDate' | 'name' | 'createdAt') => void;
  setSortOrder: (sortOrder: 'asc' | 'desc') => void;
  setPriorityFilter: (priorityFilter: 'all' | 'low' | 'medium' | 'high') => void;
  setTagFilter: (tagFilter: string | null) => void;
  reorderTodos: (activeId: string, overId: string) => void;
  refreshTodos: () => Promise<void>;
}

const TodoContext = createContext<TodoContextType | undefined>(undefined);

const todoReducer = (state: TodoState, action: any): TodoState => {
  switch (action.type) {
    case 'ADD_TODO':
      const newTodo: Todo = {
        id: Date.now().toString(),
        text: action.payload.text,
        description: action.payload.description,
        status: 'incomplete',
        priority: action.payload.priority || 'medium',
        dueDate: action.payload.dueDate,
        reminderDate: action.payload.reminderDate,
        tags: action.payload.tags || [],
        recurrence: action.payload.recurrence || 'none',
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      return {
        ...state,
        todos: [newTodo, ...state.todos],
      };

    case 'TOGGLE_TODO':
      return {
        ...state,
        todos: state.todos.map(todo =>
          todo.id === action.payload.id
            ? { ...todo, status: todo.status === 'complete' ? 'incomplete' : 'complete', updatedAt: new Date() }
            : todo
        ),
      };

    case 'DELETE_TODO':
      return {
        ...state,
        todos: state.todos.filter(todo => todo.id !== action.payload.id),
      };

    case 'UPDATE_TODO':
      return {
        ...state,
        todos: state.todos.map(todo =>
          todo.id === action.payload.id
            ? {
                ...todo,
                text: action.payload.text,
                description: action.payload.description ?? todo.description,
                priority: action.payload.priority ?? todo.priority,
                dueDate: action.payload.dueDate ?? todo.dueDate,
                reminderDate: action.payload.reminderDate ?? todo.reminderDate,
                tags: action.payload.tags ?? todo.tags,
                recurrence: action.payload.recurrence ?? todo.recurrence,
                updatedAt: new Date()
              }
            : todo
        ),
      };

    case 'CLEAR_COMPLETED':
      return {
        ...state,
        todos: state.todos.filter(todo => todo.status !== 'complete'),
      };

    case 'SET_FILTER':
      return {
        ...state,
        filter: action.payload.filter,
      };

    case 'REORDER_TODOS':
      const { activeId, overId } = action.payload;
      if (activeId === overId) return state;

      const oldIndex = state.todos.findIndex(item => item.id === activeId);
      const newIndex = state.todos.findIndex(item => item.id === overId);

      const newTodos = [...state.todos];
      const [movedItem] = newTodos.splice(oldIndex, 1);
      newTodos.splice(newIndex, 0, movedItem);

      return {
        ...state,
        todos: newTodos,
      };

    case 'LOAD_TODOS':
      return {
        ...state,
        todos: action.payload.todos || [],
      };

    case 'SET_SORT_BY':
      return { ...state, sortBy: action.payload };

    case 'SET_SORT_ORDER':
      return { ...state, sortOrder: action.payload };

    case 'SET_PRIORITY_FILTER':
      return { ...state, priorityFilter: action.payload };

    case 'SET_TAG_FILTER':
      return { ...state, tagFilter: action.payload };

    default:
      return state;
  }
};

export const TodoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize with default empty state for SSR, hydrate on client

  const getInitialState = (): TodoState => {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const savedState = localStorage.getItem('todoAppState');
        if (savedState) {
          return JSON.parse(savedState);
        }
      } catch (e) {
        console.warn('Could not load todo state from localStorage', e);
      }
    }
    return {
      todos: [],
      filter: 'all',
      sortBy: 'manual',
      sortOrder: 'desc',
      priorityFilter: 'all',
      tagFilter: null,
    };
  };

  const initialState: TodoState = getInitialState();

  const [state, dispatch] = useReducer(todoReducer, initialState);

  const { token } = useAuth(); // Get the authentication token

  // Load todos from backend API on initial render
  useEffect(() => {
    const fetchTodos = async () => {
      if (token) { // Only fetch if user is authenticated
        try {
          const data = await apiClient.getTasks();
          const fetchedTodos = data.tasks || [];

          // Convert dates from string to Date objects and map backend fields to frontend fields
          const todosWithDates = fetchedTodos.map((todo: any) => ({
            id: todo.id.toString(), // Ensure ID is a string
            text: todo.title,
            description: todo.description,
            status: todo.completed ? 'complete' : 'incomplete',
            priority: todo.priority || 'medium',
            dueDate: todo.due_date ? new Date(todo.due_date) : undefined,
            reminderDate: todo.reminder_date ? new Date(todo.reminder_date) : undefined,
            tags: todo.tags || [],
            recurrence: todo.recurrence || 'none',
            createdAt: new Date(todo.created_at),
            updatedAt: new Date(todo.updated_at),
          }));

          dispatch({ type: 'LOAD_TODOS', payload: { todos: todosWithDates } });
        } catch (e) {
          console.error('Failed to load todos from backend', e);
        }
      }
    };

    fetchTodos();
  }, [token]); // Fetch todos when token changes (on login/signup)

  const addTodo = async (text: string, description?: string, dueDate?: Date, reminderDate?: Date, priority?: 'low' | 'medium' | 'high', tags?: string[], recurrence?: string) => {
    // Add locally first, then sync with backend if logged in
    dispatch({
      type: 'ADD_TODO',
      payload: {
        text,
        description,
        dueDate,
        reminderDate,
        priority: priority || 'medium',
        tags: tags || [],
        recurrence: recurrence || 'none',
      }
    });

    // Show success message
    showToast(`Added: ${text.substring(0, 30)}${text.length > 30 ? '...' : ''}`, 'success');

    // If user is logged in, also add to backend
    if (token) {
      try {
        await apiClient.createTask({
          title: text,
          description: description || undefined,
          due_date: dueDate ? dueDate.toISOString() : null,
          reminder_date: reminderDate ? reminderDate.toISOString() : null,
          priority: priority || 'medium',
          tags: tags || [],
          recurrence: recurrence || 'none',
          reminder_enabled: !!reminderDate,
          status: 'incomplete'
        });
      } catch (error) {
        console.error('Failed to sync todo to backend:', error);
        showToast('Failed to sync task to server', 'warning');
      }
    }
  };

  const toggleTodo = async (id: string) => {
    const todo = state.todos.find(t => t.id === id);
    if (!todo) return;

    // Toggle locally first
    dispatch({ type: 'TOGGLE_TODO', payload: { id } });
    const newStatus = todo.status === 'complete' ? 'incomplete' : 'complete';
    const action = todo.status === 'complete' ? 'marked as incomplete' : 'completed';
    showToast(`${action.charAt(0).toUpperCase() + action.slice(1)}: ${todo.text.substring(0, 30)}${todo.text.length > 30 ? '...' : ''}`, 'info');

    // If user is logged in, also sync to backend
    if (token) {
      try {
        await apiClient.updateTaskStatus(id, { status: newStatus });
      } catch (error) {
        console.error('Failed to sync toggle to backend:', error);
        showToast('Failed to sync status to server', 'warning');
        // Status is already toggled locally, which is fine
      }
    }
  };

  const deleteTodo = async (id: string) => {
    const todo = state.todos.find(t => t.id === id);
    if (!todo) return;

    // Delete locally first
    dispatch({ type: 'DELETE_TODO', payload: { id } });
    showToast(`Deleted: ${todo.text.substring(0, 30)}${todo.text.length > 30 ? '...' : ''}`, 'warning');

    // If user is logged in, also delete from backend
    if (token) {
      try {
        await apiClient.deleteTask(id);
      } catch (error) {
        console.error('Failed to sync deletion to backend:', error);
        showToast('Failed to sync deletion to server', 'warning');
        // Task is already deleted locally, which is fine
      }
    }
  };

  const updateTodo = async (id: string, text: string, description?: string, dueDate?: Date, reminderDate?: Date, priority?: 'low' | 'medium' | 'high', tags?: string[], recurrence?: string) => {
    const oldTodo = state.todos.find(t => t.id === id);
    if (!oldTodo) return;

    // Update locally first
    dispatch({
      type: 'UPDATE_TODO',
      payload: {
        id,
        text,
        description,
        dueDate,
        reminderDate,
        priority,
        tags,
        recurrence,
      }
    });
    showToast(`Updated: ${text.substring(0, 30)}${text.length > 30 ? '...' : ''}`, 'success');

    // If user is logged in, also update backend
    if (token) {
      try {
        await apiClient.updateTask(id, {
          title: text,
          description: description ?? oldTodo.description,
          due_date: dueDate ? dueDate.toISOString() : null,
          reminder_date: reminderDate ? reminderDate.toISOString() : null,
          priority: priority ?? oldTodo.priority ?? 'medium',
          tags: tags ?? oldTodo.tags ?? [],
          recurrence: recurrence ?? oldTodo.recurrence ?? 'none',
          reminder_enabled: !!(reminderDate || oldTodo.reminderDate),
        });
      } catch (error) {
        console.error('Failed to sync update to backend:', error);
        showToast('Failed to sync update to server', 'warning');
      }
    }
  };

  const clearCompleted = async () => {
    if (token) { // Only show warning if logged in and trying to clear
      try {
        // Get completed tasks to delete
        const completedTodos = state.todos.filter(todo => todo.status === 'complete');

        // Delete each completed task individually (since backend doesn't have a bulk delete endpoint)
        const promises = completedTodos.map(todo =>
          apiClient.deleteTask(todo.id)
        );

        await Promise.all(promises);

        dispatch({ type: 'CLEAR_COMPLETED' });
        showToast(`Cleared ${completedTodos.length} completed tasks`, 'info');
      } catch (error) {
        console.error('Failed to clear completed todos:', error);
        showToast('Failed to clear completed tasks', 'error');
      }
    } else {
      // Clear locally without backend sync
      const completedCount = state.todos.filter(todo => todo.status === 'complete').length;
      if (completedCount > 0) {
        dispatch({ type: 'CLEAR_COMPLETED' });
        showToast(`Cleared ${completedCount} completed tasks`, 'info');
      }
    }
  };

  const setFilter = (filter: 'all' | 'active' | 'completed') => {
    dispatch({ type: 'SET_FILTER', payload: { filter } });
  };

  const setSortBy = (sortBy: 'manual' | 'priority' | 'dueDate' | 'name' | 'createdAt') => {
    dispatch({ type: 'SET_SORT_BY', payload: sortBy });
  };

  const setSortOrder = (sortOrder: 'asc' | 'desc') => {
    dispatch({ type: 'SET_SORT_ORDER', payload: sortOrder });
  };

  const setPriorityFilter = (priorityFilter: 'all' | 'low' | 'medium' | 'high') => {
    dispatch({ type: 'SET_PRIORITY_FILTER', payload: priorityFilter });
  };

  const setTagFilter = (tagFilter: string | null) => {
    dispatch({ type: 'SET_TAG_FILTER', payload: tagFilter });
  };

  const reorderTodos = (activeId: string, overId: string) => {
    // For now, just reorder locally since backend doesn't have a reorder endpoint
    // In a real implementation, we would call an API endpoint to persist the order
    dispatch({ type: 'REORDER_TODOS', payload: { activeId, overId } });
    showToast('Task reordered', 'info');
  };

  const refreshTodos = async () => {
    // Reload todos from backend API
    try {
      console.log('Refreshing todos...'); // Debug log

      // Re-fetch the token in case it has been updated
      let tokenFromStorage = localStorage.getItem('token');
      if (!tokenFromStorage) {
        tokenFromStorage = localStorage.getItem('access_token');
      }

      console.log('Token found:', !!tokenFromStorage); // Debug log

      if (!tokenFromStorage) {
        console.warn('No token available, cannot refresh todos');
        return;
      }

      const data = await apiClient.getTasks();
      console.log('Fetched data from API:', data); // Debug log

      // The backend returns an array directly, not wrapped in a 'tasks' property
      const fetchedTodos = Array.isArray(data) ? data : (data.tasks || []);
      console.log('Raw fetched todos array:', fetchedTodos); // Debug log
      if (fetchedTodos.length > 0) {
        console.log('Sample todo object:', fetchedTodos[0]); // Debug log
      }

      // Convert dates from string to Date objects and map backend fields to frontend fields
      const todosWithDates = fetchedTodos.map((todo: any) => {
        try {
          return {
            id: todo.id?.toString() || '', // Ensure ID is a string
            text: todo.title || '',
            description: todo.description || '',
            status: todo.completed ? 'complete' : 'incomplete',
            priority: todo.priority || 'medium',
            dueDate: todo.due_date ? new Date(todo.due_date) : undefined,
            reminderDate: todo.reminder_date ? new Date(todo.reminder_date) : undefined,
            tags: todo.tags || [],
            recurrence: todo.recurrence || 'none',
            createdAt: new Date(todo.created_at),
            updatedAt: new Date(todo.updated_at),
          };
        } catch (mappingError) {
          console.error('Error mapping todo:', mappingError, 'Todo data:', todo);
          return null; // Return null for failed mappings
        }
      }).filter(Boolean); // Filter out any null values

      console.log('Converted todos:', todosWithDates); // Debug log
      dispatch({ type: 'LOAD_TODOS', payload: { todos: todosWithDates } });

      console.log(`Refreshed ${todosWithDates.length} todos from backend`); // Debug log
    } catch (e) {
      console.error('Failed to refresh todos from backend', e);
      showToast('Failed to refresh tasks', 'error');
    }
  };

  const value = {
    state,
    addTodo,
    toggleTodo,
    deleteTodo,
    updateTodo,
    clearCompleted,
    setFilter,
    setSortBy,
    setSortOrder,
    setPriorityFilter,
    setTagFilter,
    reorderTodos,
    refreshTodos,
  };

  // Effect to save state to localStorage whenever it changes (only in browser)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('todoAppState', JSON.stringify(state));
      } catch (e) {
        console.warn('Could not save todo state to localStorage', e);
      }
    }
  }, [state]);

  return <TodoContext.Provider value={value}>{children}</TodoContext.Provider>;
};

export const useTodo = (): TodoContextType => {
  const context = useContext(TodoContext);
  if (!context) {
    throw new Error('useTodo must be used within a TodoProvider');
  }
  return context;
};