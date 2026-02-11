import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTodo } from '../contexts/TodoContext';
import apiClient from '../lib/apiClient';
import EventToast, { useEventToasts } from './EventToast';

const EVENT_LABELS = {
  'task.created': 'Created',
  'task.updated': 'Updated',
  'task.completed': 'Completed',
  'task.deleted': 'Deleted',
};

const EVENT_COLORS = {
  'task.created': 'bg-green-100 text-green-800',
  'task.updated': 'bg-blue-100 text-blue-800',
  'task.completed': 'bg-purple-100 text-purple-800',
  'task.deleted': 'bg-red-100 text-red-800',
};

const FloatingChatButton = ({ userId, userToken }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const { refreshTodos } = useTodo();
  const [toasts, addToast, dismissToast] = useEventToasts(5000);

  // SSE connection for real-time event updates
  useEffect(() => {
    if (!userId) return;

    const es = apiClient.connectEventStream(userId, (event) => {
      addToast(event);
      refreshTodos().catch((err) =>
        console.error('Error refreshing todos from SSE:', err)
      );
    });

    es.onopen = () => setSseConnected(true);
    es.onerror = () => setSseConnected(false);
    eventSourceRef.current = es;

    return () => {
      es.close();
      setSseConnected(false);
    };
  }, [userId]);

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const data = await apiClient.sendChatMessage(userId, inputValue, conversationId);

      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        tool_calls: data.tool_calls || [],
        events_published: data.events_published || [],
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Refresh todos when task-modifying events were published
      if (data.events_published && data.events_published.length > 0) {
        setTimeout(async () => {
          try {
            await refreshTodos();
          } catch (error) {
            console.error('Failed to refresh tasks after event:', error);
          }
        }, 300);
      }
    } catch (err) {
      const errorMessage = {
        id: Date.now(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message}`,
        timestamp: new Date().toISOString(),
        isError: true
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <>
      {/* Toast notifications from SSE events */}
      <EventToast toasts={toasts} onDismiss={dismissToast} />

      {/* Floating Chat Button */}
      <motion.button
        onClick={toggleChat}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-navy-blue text-white rounded-full shadow-lg flex items-center justify-center hover:bg-orange hover:text-navy-blue transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-navy-blue floating-chat-button"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        aria-label="Open chat"
      >
        💬
      </motion.button>

      {/* Chat Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0, y: 50 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.8, opacity: 0, y: 50 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="pointer-events-auto w-full max-w-md h-96 bg-white dark:bg-navy-blue rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col"
            >
              {/* Chat Header */}
              <div className="bg-navy-blue text-white p-4 rounded-t-lg flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">🤖</span>
                  <h3 className="font-semibold">AI Assistant</h3>
                  {sseConnected && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-green-300">
                      <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
                      Live
                    </span>
                  )}
                </div>
                <button
                  onClick={toggleChat}
                  className="text-white hover:text-gray-300 focus:outline-none"
                >
                  ✕
                </button>
              </div>

              {/* Messages Container */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-white dark:bg-navy-blue">
                {messages.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <div className="w-12 h-12 bg-navy-blue text-white rounded-full flex items-center justify-center mx-auto mb-3">
                      💬
                    </div>
                    <p className="text-sm">Start a conversation with your AI assistant</p>
                    <p className="text-xs mt-1 opacity-60">Try: "add task Buy milk #shopping high priority"</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                          message.role === 'user'
                            ? 'bg-navy-blue text-white'
                            : message.isError
                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100'
                            : 'bg-peach text-navy-blue'
                        }`}
                      >
                        <div className="whitespace-pre-wrap break-words text-sm">{message.content}</div>

                        {/* Tool call badges */}
                        {message.tool_calls && message.tool_calls.length > 0 && (
                          <div className="mt-1.5 pt-1.5 border-t border-current/20 text-xs opacity-75">
                            Actions: {message.tool_calls.map(tc => tc.name).join(', ')}
                          </div>
                        )}

                        {/* Event badges */}
                        {message.events_published && message.events_published.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {message.events_published.map((ev, i) => (
                              <span
                                key={i}
                                className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                  EVENT_COLORS[ev.event_type] || 'bg-gray-100 text-gray-800'
                                }`}
                              >
                                {EVENT_LABELS[ev.event_type] || ev.event_type}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : message.isError ? 'text-red-600 dark:text-red-300' : 'text-navy-blue/70'}`}>
                          {formatTimestamp(message.timestamp)}
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}

                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="bg-peach text-navy-blue px-3 py-2 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-navy-blue rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-navy-blue rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-navy-blue rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span>Typing...</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Input Form */}
              <form onSubmit={handleSubmit} className="border-t border-gray-200 dark:border-gray-700 p-3">
                <div className="flex space-x-2">
                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Type your message..."
                    disabled={isLoading}
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-navy-blue focus:border-transparent bg-white dark:bg-navy-blue text-navy-blue dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  />
                  <button
                    type="submit"
                    disabled={!inputValue.trim() || isLoading}
                    className="bg-navy-blue text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 hover:bg-orange hover:text-navy-blue disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Send
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default FloatingChatButton;
