import { useState, useRef, useEffect } from 'react';

// Try to detect the API port dynamically, fallback to 8001
const API_BASE = 'http://localhost:8000';

const ChatTerminal = () => {
  const [messages, setMessages] = useState([
    { 
      text: 'Hello! I\'m your AI assistant. How can I help you today?', 
      sender: 'agent',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const seenResponsesRef = useRef(new Set());

  // helper: extract response text from various server shapes
  const extractResponseText = (task, taskDetail) => {
    // direct metadata.result (server stores result under metadata.result or result)
    const tryPaths = [
      () => task?.metadata?.result?.response_text,
      () => task?.metadata?.result?.response,
      () => task?.result?.response_text,
      () => task?.result?.response,
      () => taskDetail?.metadata?.result?.response_text,
      () => taskDetail?.metadata?.result?.response,
      () => {
        // fallback: check last progress entries for result
        const prog = (taskDetail?.progress || []).slice().reverse();
        for (const p of prog) {
          if (p?.data?.result?.response_text) return p.data.result.response_text;
          if (p?.data?.result?.response) return (typeof p.data.result.response === 'string') ? p.data.result.response : JSON.stringify(p.data.result.response);
          if (p?.data?.result) return typeof p.data.result === 'string' ? p.data.result : JSON.stringify(p.data.result);
        }
        return null;
      }
    ];
    for (const fn of tryPaths) {
      try {
        const val = fn();
        if (val) return (typeof val === 'string') ? val : JSON.stringify(val);
      } catch (e) { /* ignore */ }
    }
    return null;
  };

  useEffect(() => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/tasks?limit=10`);
        if (!response.ok) return;
        const data = await response.json();
        if (!data.tasks || data.tasks.length === 0) return;

        for (const task of data.tasks) {
          // Build a unique key based on task updated time (server may update metadata.result)
          const taskKeyBase = `task-${task.id}-${task.updated_at || task.metadata?.completed_at || ''}`;

          // fetch task details to inspect progress and metadata
          const taskDetailResponse = await fetch(`${API_BASE}/task/${task.id}`);
          const taskDetail = taskDetailResponse.ok ? await taskDetailResponse.json() : null;

          // extract agent response (if any)
          const responseText = extractResponseText(task, taskDetail);

          if (responseText) {
            // dedupe by task id + response text (or timestamp if available)
            const respStamp = (task.metadata?.result?.timestamp) || (task.result?.timestamp) || (taskDetail?.progress?.slice(-1)?.[0]?.timestamp) || task.updated_at || '';
            const seenKey = `resp-${task.id}-${respStamp}-${responseText.slice(0,80)}`;

            if (!seenResponsesRef.current.has(seenKey)) {
              seenResponsesRef.current.add(seenKey);

              // insert AI assistant message with the real response
              const aiMessage = {
                id: `task-response-${task.id}-${Date.now()}`,
                text: responseText,
                sender: 'agent',
                timestamp: new Date(respStamp || Date.now()),
                taskId: task.id,
                status: task.status || 'completed',
                metadata: task.metadata || {}
              };

              setMessages(prev => {
                // remove any previous system/task placeholder for this task (id: task-<id>)
                const filtered = prev.filter(m => m.id !== `task-${task.id}`);
                return [...filtered, aiMessage];
              });

              // also update/insert a compact task system message (for list view)
              setMessages(prev => {
                const sysId = `task-${task.id}`;
                const existingIndex = prev.findIndex(m => m.id === sysId);
                const sysMsg = {
                  id: sysId,
                  text: `[${(task.status || 'COMPLETED').toUpperCase()}] ${task.description || task.title || ''}`,
                  sender: 'system',
                  timestamp: new Date(task.updated_at || Date.now()),
                  taskId: task.id,
                  status: task.status || 'completed',
                  metadata: task.metadata || {}
                };
                if (existingIndex >= 0) {
                  const copy = [...prev];
                  copy[existingIndex] = { ...copy[existingIndex], ...sysMsg };
                  return copy;
                }
                return [...prev, sysMsg];
              });
            }
            continue;
          }

          // If no response yet but task changed (status update), update or insert system message
          const taskSysKey = `task-${task.id}-${task.updated_at}`;
          if (!seenResponsesRef.current.has(taskSysKey)) {
            seenResponsesRef.current.add(taskSysKey);

            const taskMessage = {
              id: `task-${task.id}`,
              text: `[${(task.status || 'PENDING').toUpperCase()}] ${task.description || task.title || ''}`,
              sender: 'system',
              timestamp: new Date(task.updated_at || Date.now()),
              taskId: task.id,
              status: task.status || 'pending',
              metadata: task.metadata || {}
            };

            setMessages(prev => {
              const existingIndex = prev.findIndex(msg => msg.id === taskMessage.id);
              if (existingIndex >= 0) {
                const newMessages = [...prev];
                newMessages[existingIndex] = {
                  ...newMessages[existingIndex],
                  ...taskMessage,
                  timestamp: newMessages[existingIndex].timestamp
                };
                return newMessages;
              } else {
                return [...prev, taskMessage];
              }
            });
          }
        }
      } catch (error) {
        console.error('Error polling task updates:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const taskText = inputValue.trim();
    const taskTimestamp = new Date();

    // Add user message
    const userMessage = {
      id: `user-${Date.now()}`,
      text: taskText,
      sender: 'user',
      timestamp: taskTimestamp,
      type: 'user_input'
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: taskText, timestamp: taskTimestamp.toISOString() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to create task');
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        text: `Error: ${error.message}`,
        sender: 'agent',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (date) => {
    if (!(date instanceof Date)) date = new Date(date);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  // Format message content with proper line breaks
  const formatMessageText = (text) => {
    if (!text) return '';
    return text.split('\n').map((line, i) => (
      <span key={i}>
        {line}
        <br />
      </span>
    ));
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'rgba(10, 25, 47, 0.8)',
      borderRadius: '12px',
      border: '1px solid rgba(100, 255, 218, 0.2)',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
    }}>
      <div style={{
        padding: '15px 20px',
        backgroundColor: 'rgba(10, 25, 47, 0.9)',
        borderBottom: '1px solid rgba(100, 255, 218, 0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ color: '#64ffda', fontWeight: 'bold', fontSize: '1.1rem' }}>
          AI Village Task Runner
        </div>
      </div>
      
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '15px'
      }}>
        {messages.map((message) => (
          <div 
            key={message.id} 
            style={{
              padding: '14px 18px',
              borderRadius: '10px',
              backgroundColor: message.sender === 'user' 
                ? 'rgba(30, 144, 255, 0.15)' 
                : message.status === 'failed' 
                  ? 'rgba(255, 71, 87, 0.15)'
                  : message.status === 'completed'
                    ? 'rgba(100, 255, 218, 0.15)'
                    : 'rgba(100, 120, 150, 0.1)',
              borderLeft: `3px solid ${message.sender === 'user' ? '#1e90ff' : '#64ffda'}`,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: message.sender === 'user' ? '#1e90ff' : '#64ffda'
            }}
          >
            <div style={{ 
              fontSize: '0.85rem', 
              marginBottom: '8px',
              opacity: 0.8,
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <span style={{ fontWeight: 'bold' }}>
                {message.sender === 'user' ? 'You' : (message.sender === 'agent' ? 'AI Assistant' : 'System')}
              </span>
              <span>{formatTime(message.timestamp)}</span>
            </div>
            <div style={{ fontSize: '0.95rem', wordBreak: 'break-word' }}>
              {formatMessageText(message.text)}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} style={{
        padding: '15px',
        backgroundColor: 'rgba(10, 25, 47, 0.9)',
        borderTop: '1px solid rgba(100, 255, 218, 0.2)',
        display: 'flex',
        gap: '10px'
      }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter a task for the CUA agents..."
          disabled={isLoading}
          autoFocus
          style={{
            flex: 1,
            padding: '12px 15px',
            backgroundColor: 'rgba(10, 25, 47, 0.8)',
            border: '1px solid rgba(100, 255, 218, 0.2)',
            borderRadius: '8px',
            color: '#ccd6f6',
            fontSize: '0.95rem',
            outline: 'none'
          }}
        />
        <button 
          type="submit" 
          disabled={!inputValue.trim() || isLoading}
          style={{
            padding: '12px 20px',
            backgroundColor: isLoading ? '#444' : '#64ffda',
            color: '#0a192f',
            border: 'none',
            borderRadius: '8px',
            cursor: isLoading || !inputValue.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </form>
    </div>
  );
};

export default ChatTerminal;
