import { useState, useRef, useEffect } from 'react';

const ChatTerminal = () => {
  const [messages, setMessages] = useState([
    { 
      text: 'Hello! I\'m your AI assistant. How can I help you today?', 
      sender: 'agent',
      timestamp: new Date()
    }
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    // Simulate agent thinking
    const thinkingMessage = {
      id: Date.now() + 0.5,
      text: '...',
      sender: 'agent',
      timestamp: new Date(),
      isThinking: true
    };
    
    setMessages(prev => [...prev, thinkingMessage]);

    // Simulate agent response after delay
    setTimeout(() => {
      const responses = [
        'I understand you want to generate an image. Could you provide more details about the style and composition?',
        'That sounds interesting! What kind of mood or atmosphere are you envisioning?',
        'I can help with that. Any specific colors, lighting, or artistic influences you want to include?',
        'Great choice! I\'ll generate a few variations based on your description.',
        'I can create that for you. Would you like to adjust any details before I proceed?'
      ];
      
      // Remove thinking message
      setMessages(prev => prev.filter(msg => !msg.isThinking));
      
      const agentMessage = {
        id: Date.now() + 1,
        text: responses[Math.floor(Math.random() * responses.length)],
        sender: 'agent',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, agentMessage]);
    }, 1500 + Math.random() * 1000);
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-terminal">
      <div className="terminal-header">
        <div className="terminal-buttons">
          <span className="close-btn"></span>
          <span className="minimize-btn"></span>
          <span className="expand-btn"></span>
        </div>
        <div className="terminal-title">AI Image Assistant</div>
      </div>
      
      <div className="messages">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`message ${message.sender} ${message.isThinking ? 'thinking' : ''}`}
          >
            <div className="message-header">
              <span className="sender">
                {message.sender === 'user' ? 'You' : 'AI Assistant'}
              </span>
              <span className="timestamp">
                {!message.isThinking && formatTime(message.timestamp)}
              </span>
            </div>
            <div className="message-content">
              {message.text}
              {message.isThinking && (
                <span className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="chat-input-container">
        <div className="input-wrapper">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Describe the image you want to generate..."
            autoFocus
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={!inputValue.trim()}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatTerminal;
