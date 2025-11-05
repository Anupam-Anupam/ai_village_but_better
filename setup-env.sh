#!/bin/bash

# Setup script for CUA Agent Template
# This script helps you create the necessary environment file

echo "Setting up CUA Agent Template environment..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# CUA Agent Template Environment Variables
# Fill in your actual values below

# Required: CUA API Configuration
CUA_API_KEY=your_cua_api_key_here
CUA_SANDBOX_NAME=your_sandbox_name_here

# Required: OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Display Configuration (for GUI applications)
DISPLAY=:99

# Optional: Logging Configuration
LOG_LEVEL=INFO

# Optional: Agent Configuration
MAX_TRAJECTORY_BUDGET=1.0
ONLY_N_MOST_RECENT_IMAGES=3
EOF
    echo "✅ Created .env file"
else
    echo "⚠️  .env file already exists"
fi

# Create necessary directories
mkdir -p trajectories logs

echo "✅ Created trajectories and logs directories"

echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual API keys"
echo "2. Run: docker-compose up --build"
echo "   or: docker build -t cua-agent-template . && docker run --env-file .env cua-agent-template"
echo ""
echo "For more information, see DOCKER.md"

