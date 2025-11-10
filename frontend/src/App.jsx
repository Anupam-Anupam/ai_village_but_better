import AgentLiveFeed from './components/AgentLiveFeed';
import ChatPopup from './components/ChatPopup';
import './App.css';

function App() {
  return (
    <div className="app">
      <div className="background-gradient" aria-hidden="true">
        <div className="gradient-1" />
        <div className="gradient-2" />
        <div className="gradient-3" />
      </div>

      <main className="app-main">
        <AgentLiveFeed />
      </main>

      <ChatPopup />
    </div>
  );
}

export default App;
