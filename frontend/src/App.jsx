import { useState } from 'react';
import ChatTerminal from './components/ChatTerminal';
import ScreenshotViewer from './components/ScreenshotViewer';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div style={{ 
      minHeight: '100vh', 
      width: '100%',
      display: 'flex', 
      flexDirection: 'column',
      backgroundColor: '#0a192f',
      color: '#ccd6f6',
      padding: '20px',
      boxSizing: 'border-box'
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        width: '100%', 
        margin: '0 auto', 
        flex: 1,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1 style={{ 
            color: '#64ffda',
            fontSize: '2rem',
            fontWeight: 'bold',
            margin: 0
          }}>
            AI Village Task Runner
          </h1>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={() => setActiveTab('chat')}
              style={{
                padding: '8px 16px',
                backgroundColor: activeTab === 'chat' ? '#64ffda' : 'transparent',
                color: activeTab === 'chat' ? '#0a192f' : '#64ffda',
                border: `1px solid #64ffda`,
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.2s ease-in-out',
                ':hover': {
                  backgroundColor: activeTab === 'chat' ? '#64ffda' : '#64ffda20'
                }
              }}
            >
              Chat
            </button>
            <button 
              onClick={() => setActiveTab('screenshots')}
              style={{
                padding: '8px 16px',
                backgroundColor: activeTab === 'screenshots' ? '#64ffda' : 'transparent',
                color: activeTab === 'screenshots' ? '#0a192f' : '#64ffda',
                border: `1px solid #64ffda`,
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.2s ease-in-out',
                ':hover': {
                  backgroundColor: activeTab === 'screenshots' ? '#64ffda' : '#64ffda20'
                }
              }}
            >
              Screenshots
            </button>
          </div>
        </div>
        
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column',
          backgroundColor: '#112240',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          {activeTab === 'chat' ? (
            <ChatTerminal />
          ) : (
            <ScreenshotViewer />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
