import { useState, useEffect } from 'react';
import ChatTerminal from './components/ChatTerminal';
import ImageCards from './components/ImageCards';
import './App.css';

function App() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  
  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="app">
      {/* Animated background gradient */}
      <div 
        className="background-gradient"
        style={{
          '--mouse-x': `${mousePosition.x}px`,
          '--mouse-y': `${mousePosition.y}px`,
        }}
      >
        <div className="gradient-1"></div>
        <div className="gradient-2"></div>
        <div className="gradient-3"></div>
      </div>
      
      <div className="app-container">
        <main className="main-content">
          <div className="content-wrapper">
            <h1>AI Image Generator</h1>
            <div className="image-section">
              <ImageCards />
            </div>
          </div>
        </main>
        
        <aside className="chat-sidebar">
          <ChatTerminal />
        </aside>
      </div>
    </div>
  );
}

export default App;
