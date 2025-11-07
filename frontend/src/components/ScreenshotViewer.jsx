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
      // Use the server's /screenshots/list endpoint
      console.log('Fetching screenshots...');
      const response = await fetch('http://localhost:8000/screenshots/list');
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch screenshots:', errorText);
        throw new Error(`Failed to fetch screenshots: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      console.log('Received screenshot data:', data);
      
      // Update screenshots with new URLs and timestamps
      const updatedScreenshots = { ...screenshots };
      let hasUpdates = false;
      
      for (const agent of ['agent1', 'agent2', 'agent3']) {
        if (data[agent] && data[agent].url) {
          // Ensure the URL is accessible from the browser
          let publicUrl = data[agent].url;
          
          // Replace internal Docker hostnames with localhost if needed
          publicUrl = publicUrl.replace('http://minio:9000', 'http://localhost:9000');
          
          // Add timestamp to force image refresh
          const timestamp = new Date().getTime();
          const imageUrl = `${publicUrl}${publicUrl.includes('?') ? '&' : '?'}_t=${timestamp}`;
          
          console.log(`Updating ${agent} screenshot URL:`, imageUrl);
          
          // Only update if the URL has changed to avoid unnecessary re-renders
          if (updatedScreenshots[agent].url !== imageUrl) {
            updatedScreenshots[agent] = {
              url: imageUrl,
              timestamp: data[agent].lastModified
            };
            hasUpdates = true;
          }
        } else {
          console.log(`No screenshot data for ${agent}`);
        }
      }
      
      if (hasUpdates) {
        setScreenshots(updatedScreenshots);
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
        {['agent1', 'agent2', 'agent3'].map((agent) => (
          <div key={agent} style={styles.card}>
            <h3 style={styles.agentName}>{agent}</h3>
            <div style={styles.imageContainer}>
              {screenshots[agent].url ? (
                <img
                  src={screenshots[agent].url}
                  alt={`${agent} screenshot`}
                  style={styles.image}
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg width=\'400\' height=\'300\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Crect width=\'100%25\' height=\'100%25\' fill=\'%23112d4e\'/%3E%3Ctext x=\'50%25\' y=\'50%25\' font-family=\'sans-serif\' font-size=\'16\' text-anchor=\'middle\' dominant-baseline=\'middle\' fill=\'%2364ffda\'%3ENo image available%3C/text%3E%3C/svg%3E';
                  }}
                />
              ) : (
                <div style={styles.placeholder}>
                  {isLoading ? 'Loading...' : 'No screenshot available'}
                </div>
              )}
            </div>
            <div style={styles.timestamp}>
              Last updated: {formatTime(screenshots[agent].timestamp)}
            </div>
          </div>
        ))}
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
