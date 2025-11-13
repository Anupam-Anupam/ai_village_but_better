import AgentLiveFeed from './components/AgentLiveFeed';
import ChatTerminal from './components/ChatTerminal';
import './App.css';

function App() {
  return (
    <div className="app">
      <div className="background-gradient" aria-hidden="true">
        <div className="gradient-1" />
        <div className="gradient-2" />
        <div className="gradient-3" />
      </div>

      <div className="app-layout">
        {/* Left Side: Live Agent Feeds */}
        <aside className="app-layout__left">
          <AgentLiveFeed />
        </aside>

        {/* Right Side: Chat Interface */}
        <aside className="app-layout__right">
          <ChatTerminal />
        </aside>
      </div>
    </div>
  );
}

export default App;
