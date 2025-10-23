#!/bin/bash

echo "🤖 Setting up Agent Databases with MongoDB"
echo "=========================================="

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_URL=mongodb://admin:password@mongodb:27017/hubdb
EOF
    echo "⚠️  Please update .env with your actual OpenAI API key"
fi

# Start the main MongoDB database
echo "Starting main MongoDB database..."
docker-compose up -d mongodb

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
sleep 10

# Test MongoDB connection
echo "Testing MongoDB connection..."
docker-compose exec mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Main MongoDB database connected"
else
    echo "❌ Main MongoDB database connection failed"
fi

echo ""
echo "🎉 MongoDB setup complete!"
echo ""
echo "Database connections:"
echo "  - Main Hub MongoDB: localhost:27017 (admin/password)"
echo "  - Each agent has its own embedded MongoDB instance"
echo ""
echo "To start all services:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f agent1"
echo "  docker-compose logs -f agent2"
echo "  docker-compose logs -f agent3"
echo ""
echo "To test agent endpoints:"
echo "  curl http://localhost:8001/tasks"
echo "  curl http://localhost:8001/memory"
echo "  curl http://localhost:8001/config"
