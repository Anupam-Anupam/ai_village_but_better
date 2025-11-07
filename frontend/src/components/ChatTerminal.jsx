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
  const inputRef = useRef(null);
  const seenResponsesRef = useRef(new Set());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Poll for task updates
  useEffect(() => {
    const pollInterval = setInterval(async () => {
      try {
        // Get recent tasks
        const response = await fetch(`${API_BASE}/tasks?limit=5`);
        const data = await response.json();
        
        if (data.tasks && data.tasks.length > 0) {
          // Process the most recent task
          const latestTask = data.tasks[0];
          
          // Create a unique key for this task update
          const taskKey = `task-${latestTask.id}-${latestTask.updated_at}`;
          
          if (!seenResponsesRef.current.has(taskKey)) {
            seenResponsesRef.current.add(taskKey);
            
            // Add task update to messages
            const taskMessage = {
              id: `task-${latestTask.id}`,
              text: `[Task ${latestTask.status}] ${latestTask.title}`,
              sender: 'system',
              timestamp: new Date(latestTask.updated_at),
              taskId: latestTask.id
            };
            
            setMessages(prev => {
              // Check if this task update already exists
              const exists = prev.some(msg => 
                msg.id === taskMessage.id && 
                msg.text === taskMessage.text
              );
              if (exists) return prev;
              
              // Replace previous message for this task if it exists
              return [
                ...prev.filter(msg => msg.id !== taskMessage.id),
                taskMessage
              ];
            });
          }
        }
      } catch (error) {
        console.error('Error polling task updates:', error);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const taskText = inputValue.trim();

    // Add user message
    const userMessage = {
      id: Date.now(),
      text: taskText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Add thinking message
    const thinkingMessage = {
      id: Date.now() + 0.5,
      text: 'Sending task to agents...',
      sender: 'agent',
      timestamp: new Date(),
      isThinking: true
    };
    
    setMessages(prev => [...prev, thinkingMessage]);

    try {
      // Create a new task via the API
      const response = await fetch(`${API_BASE}/task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: taskText }),
      });

      const data = await response.json();

      // Remove thinking message
      setMessages(prev => prev.filter(msg => !msg.isThinking));

      if (response.ok) {
        // Add the task to the UI
        const taskMessage = {
          id: `task-${data.task_id}`,
          text: `[Task created] ${taskText}`,
          sender: 'system',
          timestamp: new Date(),
          taskId: data.task_id
        };
        
        setMessages(prev => [...prev, taskMessage]);
      } else {
        throw new Error(data.detail || 'Failed to create task');
      }
    } catch (error) {
      // Remove thinking message
      setMessages(prev => prev.filter(msg => !msg.isThinking));
      
      // Add error message
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
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: message.sender === 'user' 
                ? 'rgba(30, 144, 255, 0.1)' 
                : 'rgba(100, 255, 218, 0.1)',
              borderLeft: `3px solid ${message.sender === 'user' ? '#1e90ff' : '#64ffda'}`,
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
                {message.sender === 'user' ? 'You' : 'AI Assistant'}
              </span>
              {!message.isThinking && (
                <span>{formatTime(message.timestamp)}</span>
              )}
            </div>
            <div style={{ fontSize: '0.95rem', wordBreak: 'break-word' }}>
              {message.text}
              {message.isThinking && (
                <span style={{ display: 'inline-flex', gap: '4px', marginLeft: '8px' }}>
                  <span style={{ animation: 'blink 1.4s infinite' }}>.</span>
                  <span style={{ animation: 'blink 1.4s infinite 0.2s' }}>.</span>
                  <span style={{ animation: 'blink 1.4s infinite 0.4s' }}>.</span>
                </span>
              )}
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
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 0; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default ChatTerminal;
