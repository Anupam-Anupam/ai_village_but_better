import { useState, useEffect } from 'react';

const ScreenshotViewer = () => {
  const [screenshots, setScreenshots] = useState({
    agent1: { url: '', timestamp: null },
    agent2: { url: '', timestamp: null },
    agent3: { url: '', timestamp: null }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchScreenshots = async () => {
    try {
      setIsLoading(true);
      const updatedScreenshots = { ...screenshots };
      
      // Agent configuration
      const agents = ['agent1', 'agent2', 'agent3'];
      
      for (const agent of agents) {
        try {
          // Use the server's screenshot endpoint with cache-busting
          const response = await fetch(`http://localhost:8000/agent-screenshot/${agent}?t=${Date.now()}`, {
            method: 'GET',
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
              'Expires': '0'
            },
            credentials: 'include'  // Include cookies if needed for auth
          });
          
          if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            updatedScreenshots[agent] = {
              url: url,
              timestamp: new Date().toISOString()
            };
          } else {
            console.warn(`Failed to fetch screenshot from ${agent}:`, response.status);
            updatedScreenshots[agent] = {
              url: '',
              timestamp: new Date().toISOString(),
              error: `Failed to load: ${response.status} ${response.statusText}`
            };
          }
        } catch (err) {
          console.error(`Error fetching from ${agent}:`, err);
          updatedScreenshots[agent] = {
            ...updatedScreenshots[agent],
            error: `Connection error: ${err.message}`
          };
        }
      }
      
      setScreenshots(updatedScreenshots);
      setError(null);
    } catch (err) {
      console.error('Error fetching screenshots:', err);
      setError('Failed to load screenshots. Make sure MinIO is running.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchScreenshots();
    
    // Set up polling every 5 seconds
    const interval = setInterval(fetchScreenshots, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Agent Screenshots</h2>
      {error && <div style={styles.error}>{error}</div>}
      
      <div style={styles.grid}>
        {['agent1', 'agent2', 'agent3'].map((agent) => {
          const agentData = screenshots[agent] || {};
          const hasError = !!agentData.error;
          const hasImage = !!agentData.url;
          
          return (
            <div key={agent} style={styles.card}>
              <h3 style={styles.agentName}>
                {agent}
                {hasError && (
                  <span style={{ 
                    fontSize: '0.7em',
                    color: '#ff6b6b',
                    marginLeft: '10px',
                    fontWeight: 'normal'
                  }}>
                    {agentData.error}
                  </span>
                )}
              </h3>
              <div style={styles.imageContainer}>
                {hasImage ? (
                  <img
                    src={`${agentData.url}?t=${new Date().getTime()}`}
                    alt={`${agent} screenshot`}
                    style={{
                      ...styles.image,
                      border: hasError ? '2px solid #ff6b6b' : 'none'
                    }}
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg width=\'400\' height=\'300\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Crect width=\'100%25\' height=\'100%25\' fill=\'%23112d4e\'/%3E%3Ctext x=\'50%25\' y=\'50%25\' font-family=\'sans-serif\' font-size=\'16\' text-anchor=\'middle\' dominant-baseline=\'middle\' fill=\'%2364ffda\'%3EImage load failed%3C/text%3E%3C/svg%3E';
                      
                      // Update state to reflect the error
                      setScreenshots(prev => ({
                        ...prev,
                        [agent]: {
                          ...prev[agent],
                          error: 'Failed to load image'
                        }
                      }));
                    }}
                  />
                ) : (
                  <div style={styles.placeholder}>
                    {isLoading ? (
                      <span>Loading...</span>
                    ) : hasError ? (
                      <span style={{ color: '#ff6b6b' }}>Error loading image</span>
                    ) : (
                      'No screenshot available'
                    )}
                  </div>
                )}
              </div>
              <div style={styles.timestamp}>
                {agentData.timestamp ? `Last updated: ${formatTime(agentData.timestamp)}` : 'Never updated'}
                {hasImage && (
                  <button 
                    onClick={() => {
                      // Force refresh this agent's screenshot
                      const timestamp = new Date().getTime();
                      setScreenshots(prev => ({
                        ...prev,
                        [agent]: {
                          ...prev[agent],
                          url: `${prev[agent].url.split('?')[0]}?t=${timestamp}`,
                          timestamp: new Date().toISOString()
                        }
                      }));
                    }}
                    style={{
                      marginLeft: '10px',
                      background: 'transparent',
                      border: '1px solid #64ffda',
                      color: '#64ffda',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.7em',
                      padding: '2px 5px'
                    }}
                  >
                    Refresh
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#0a192f',
    borderRadius: '8px',
    marginTop: '20px',
    flex: 1,
    overflowY: 'auto'
  },
  heading: {
    color: '#64ffda',
    marginBottom: '20px',
    fontSize: '1.5rem',
    fontWeight: '600'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '20px',
    width: '100%'
  },
  card: {
    backgroundColor: '#112240',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    transition: 'transform 0.2s ease-in-out',
    ':hover': {
      transform: 'translateY(-4px)'
    }
  },
  agentName: {
    backgroundColor: '#1e2b4d',
    color: '#64ffda',
    margin: 0,
    padding: '10px 15px',
    fontSize: '1rem',
    fontWeight: '500',
    textTransform: 'capitalize'
  },
  imageContainer: {
    width: '100%',
    height: '200px',
    backgroundColor: '#0a192f',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    position: 'relative'
  },
  image: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    backgroundColor: '#0a192f'
  },
  placeholder: {
    color: '#8892b0',
    fontSize: '0.9rem',
    textAlign: 'center',
    padding: '20px'
  },
  timestamp: {
    backgroundColor: '#1e2b4d',
    color: '#8892b0',
    fontSize: '0.8rem',
    padding: '8px 15px',
    textAlign: 'right'
  },
  error: {
    backgroundColor: '#ff6b6b20',
    color: '#ff6b6b',
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '20px',
    border: '1px solid #ff6b6b40'
  }
};

export default ScreenshotViewer;
