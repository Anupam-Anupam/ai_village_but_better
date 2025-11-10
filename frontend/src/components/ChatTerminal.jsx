import { useState, useRef, useEffect, useCallback } from 'react';
import { API_BASE, REFRESH_INTERVALS } from '../config';

const ensureDate = (value) => {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return new Date();
  }
  return date;
};

const normalizePercent = (value) => {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.max(0, Math.min(100, parsed));
};

const formatPercentLabel = (value) => {
  const percent = normalizePercent(value);
  if (percent === null) {
    return null;
  }
  return `${percent.toFixed(0)}%`;
};

const buildAgentMessage = (record) => {
  if (!record || record.id === undefined || record.id === null) {
    return null;
  }

  const timestamp = ensureDate(record.timestamp);
  const progressPercent = normalizePercent(record.progress_percent);
  const text = (record.message && record.message.trim().length > 0)
    ? record.message
    : (progressPercent !== null
      ? `Progress update: ${progressPercent.toFixed(0)}% complete.`
      : 'Progress update received.');

  return {
    id: `agent-response-${record.id}`,
    sender: 'agent',
    agentId: record.agent_id || 'Agent',
    text,
    timestamp,
    taskId: record.task_id ?? null,
    progressPercent,
    taskTitle: record.task?.title ?? null,
    taskStatus: record.task?.status ?? null,
  };
};

const formatTime = (date) => {
  if (!date) {
    return '—';
  }
  const safeDate = ensureDate(date);
  return safeDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const getSenderLabel = (message) => {
  if (message.sender === 'user') {
    return 'You';
  }
  if (message.sender === 'system') {
    return 'System';
  }
  return message.agentId || 'Agent';
};

const ChatTerminal = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(null);
  const messagesEndRef = useRef(null);
  const abortRef = useRef(false);

  const upsertMessages = useCallback((incoming = []) => {
    if (!incoming.length) {
      return;
    }

    setMessages((prev) => {
      const map = new Map(prev.map((msg) => [msg.id, msg]));
      incoming.forEach((msg) => {
        if (!msg || msg.id === undefined || msg.id === null) {
          return;
        }
        const timestamp = ensureDate(msg.timestamp);
        map.set(msg.id, { ...msg, timestamp });
      });

      return Array.from(map.values()).sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    });
  }, []);

  const fetchAgentResponses = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/agent-responses?limit=60`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load agent responses');
      }

      if (abortRef.current) {
        return;
      }

      const normalized = (Array.isArray(data.messages) ? data.messages : [])
        .map(buildAgentMessage)
        .filter(Boolean);

      if (normalized.length) {
        upsertMessages(normalized);
      }
      setHistoryError(null);
    } catch (error) {
      if (abortRef.current) {
        return;
      }
      console.error('Error loading agent responses:', error);
      setHistoryError(error.message || 'Unable to load agent responses');
    } finally {
      if (!abortRef.current) {
        setHistoryLoading(false);
      }
    }
  }, [upsertMessages]);

  useEffect(() => {
    abortRef.current = false;

    fetchAgentResponses();
    const intervalId = setInterval(fetchAgentResponses, REFRESH_INTERVALS.chat);

    return () => {
      abortRef.current = true;
      clearInterval(intervalId);
    };
  }, [fetchAgentResponses]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const taskText = inputValue.trim();

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: taskText,
      timestamp: new Date(),
    };

    upsertMessages([userMessage]);
    setInputValue('');
    setIsLoading(true);

    const thinkingMessage = {
      id: `thinking-${Date.now()}`,
      sender: 'system',
      text: 'Sending task to agents',
      timestamp: new Date(),
      isThinking: true,
    };

    upsertMessages([thinkingMessage]);

    try {
      const response = await fetch(`${API_BASE}/task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: taskText }),
      });

      const data = await response.json();

      setMessages((prev) => prev.filter((msg) => !msg.isThinking));

      if (response.ok) {
        const taskMessage = {
          id: `task-${data.task_id}`,
          sender: 'system',
          text: `[Task created] ${taskText}`,
          timestamp: new Date(),
          taskId: data.task_id,
        };
        upsertMessages([taskMessage]);
        fetchAgentResponses();
      } else {
        throw new Error(data.detail || 'Failed to create task');
      }
    } catch (error) {
      setMessages((prev) => prev.filter((msg) => !msg.isThinking));

      const errorMessage = {
        id: `error-${Date.now()}`,
        sender: 'system',
        text: `Error: ${error.message}`,
        timestamp: new Date(),
        isError: true,
      };
      upsertMessages([errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-terminal">
      <header className="chat-terminal__header">
        <div>
          <div className="chat-terminal__title">Agent Playground</div>
          <div className="chat-terminal__subtitle">Share a task and watch the agents report back.</div>
        </div>
      </header>

      <div className="chat-terminal__messages">
        {historyLoading && (
          <div className="chat-message chat-message--system">
            <div className="chat-message__text">Loading conversation…</div>
          </div>
        )}

        {!historyLoading && messages.length === 0 && !historyError && (
          <div className="chat-message chat-message--system">
            <div className="chat-message__text">Say hello! Agent responses will appear here as they make progress.</div>
          </div>
        )}

        {historyError && (
          <div className="chat-message chat-message--error">
            <div className="chat-message__text">{historyError}</div>
          </div>
        )}

        {messages.map((message) => {
          const classes = ['chat-message'];
          if (message.sender === 'user') {
            classes.push('chat-message--user');
          } else if (message.sender === 'system') {
            classes.push('chat-message--system');
          } else {
            classes.push('chat-message--agent');
          }
          if (message.isError) {
            classes.push('chat-message--error');
          }

          return (
            <div key={message.id} className={classes.join(' ')}>
              <div className="chat-message__top">
                <span className="chat-message__sender">{getSenderLabel(message)}</span>
                {!message.isThinking && (
                  <span className="chat-message__time">{formatTime(message.timestamp)}</span>
                )}
              </div>
              <div className="chat-message__text">
                {message.text}
                {message.isThinking && (
                  <span className="chat-message__thinking" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </span>
                )}
              </div>
              {!message.isThinking && formatPercentLabel(message.progressPercent) && (
                <span className="chat-message__progress">
                  {formatPercentLabel(message.progressPercent)}
                </span>
              )}
              {(message.taskId || message.taskTitle || message.taskStatus) && (
                <div className="chat-message__tags">
                  {message.taskId && <span>Task #{message.taskId}</span>}
                  {message.taskTitle && <span>{message.taskTitle}</span>}
                  {message.taskStatus && <span>Status: {message.taskStatus}</span>}
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-terminal__form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter a joyful mission for the agents…"
          disabled={isLoading}
          className="chat-terminal__input"
        />
        <button
          type="submit"
          disabled={!inputValue.trim() || isLoading}
          className="chat-terminal__send"
        >
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatTerminal;
