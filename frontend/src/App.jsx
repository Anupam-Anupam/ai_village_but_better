import ChatTerminal from './components/ChatTerminal';
import './App.css';

function App() {
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
        <h1 style={{ 
          marginBottom: '20px', 
          color: '#64ffda',
          fontSize: '2rem',
          fontWeight: 'bold'
        }}>
          AI Village Task Runner
        </h1>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <ChatTerminal />
        </div>
      </div>
    </div>
  );
}

export default App;
