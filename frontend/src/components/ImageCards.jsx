import { useState, useEffect } from 'react';

const ImageCards = () => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  // Using placeholder images from Unsplash with a tech/ai theme
  const imageSets = [
    [
      'https://images.unsplash.com/photo-1677442136018-9e0a3e2a6a9d1?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c1d?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c1e?w=800&auto=format&fit=crop'
    ],
    [
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c1f?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c20?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c21?w=800&auto=format&fit=crop'
    ],
    [
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c22?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c23?w=800&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1677442135362-9b9d8a8c3c24?w=800&auto=format&fit=crop'
    ]
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prevIndex) => (prevIndex + 1) % imageSets.length);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="image-cards">
      {imageSets[currentImageIndex].map((img, index) => (
        <div key={`${currentImageIndex}-${index}`} className="image-card">
          <div className="image-container">
            <img 
              src={img} 
              alt={`Generated content ${index + 1}`}
              loading="lazy"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = `https://via.placeholder.com/800x600/112240/64ffda?text=AI+Image+${index + 1}`;
              }}
            />
            <div className="image-overlay">
              <span>AI Generated Image {index + 1}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ImageCards;
