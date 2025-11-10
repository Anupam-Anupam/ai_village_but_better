import { useState } from 'react';
import ChatTerminal from './ChatTerminal';
import '../App.css';

const ChatPopup = () => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside className={`chat-popup ${isOpen ? 'chat-popup--open' : 'chat-popup--closed'}`}>
      <header className="chat-popup__header">
        <span>Agent Chat</span>
        <button
          type="button"
          className="chat-popup__toggle"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Collapse chat' : 'Expand chat'}
        >
          {isOpen ? '−' : '+'}
        </button>
      </header>
      {isOpen && (
        <div className="chat-popup__body">
          <ChatTerminal />
        </div>
      )}
    </aside>
  );
};

export default ChatPopup;
