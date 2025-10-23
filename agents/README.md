# AI Agents with Individual MongoDB Databases

This directory contains AI agents that each run in their own Docker containers with embedded MongoDB databases.

## 🏗️ Architecture

### Database Isolation
Each agent has its own completely separate MongoDB database:
- **Agent 1**: `mongodb://localhost:27017/agent1db`
- **Agent 2**: `mongodb://localhost:27017/agent2db`
- **Agent 3**: `mongodb://localhost:27017/agent3db`

### Shared Code, Separate Data
- **`shared/`**: Contains shared database models and utilities
- **`agent1/`**: Agent 1 specific code and Dockerfile
- **`agent2/`**: Agent 2 specific code and Dockerfile
- **`agent3/`**: Agent 3 specific code and Dockerfile

## 📁 Directory Structure

```
agents/
├── shared/                    # Shared code (not data)
│   ├── models.py              # AgentDatabase class for MongoDB operations
│   ├── requirements.txt       # Common Python dependencies
│   ├── db.py                 # Database utilities
│   └── init_agent_db.py      # Database initialization script
├── agent1/                    # Agent 1 (GPT-4)
│   ├── agent.py              # FastAPI server with GPT-4 integration
│   └── Dockerfile            # Container with embedded MongoDB
├── agent2/                    # Agent 2 (Claude)
│   ├── agent.py              # FastAPI server with Claude integration
│   └── Dockerfile            # Container with embedded MongoDB
└── agent3/                    # Agent 3 (Llama)
    ├── agent.py              # FastAPI server with Llama integration
    └── Dockerfile            # Container with embedded MongoDB
```

## 🗄️ Database Structure (Per Agent)

Each agent's MongoDB database contains:

### Collections
- **`agent_tasks`**: Task storage and tracking
- **`agent_memories`**: Agent's memory window with automatic cleanup
- **`agent_config`**: Agent settings and preferences
- **`agent_logs`**: Activity and error logging

### Data Isolation
- Each agent's data is completely separate
- No data sharing between agents
- Each agent can only access its own database

## 🚀 How to Run

### 1. Start All Services
```bash
docker-compose up -d
```

### 2. Wait for Initialization
```bash
# Wait for agents to start (about 30 seconds)
sleep 30
```

### 3. Test the System
```bash
python test_mongodb_agents.py
```

## 🔧 API Endpoints (Per Agent)

Each agent exposes these endpoints:

### Task Processing
- **POST** `/execute` - Process tasks with AI model
- **GET** `/tasks` - Get agent's tasks

### Memory Management
- **GET** `/memory` - Get agent's memory
- **POST** `/memory` - Add to agent's memory

### Configuration
- **GET** `/config` - Get agent configuration
- **POST** `/config` - Update agent configuration

### Logging
- **GET** `/logs` - Get agent logs

## 🎯 Key Features

### Database Isolation
- Each agent has its own MongoDB instance
- Complete data separation
- No cross-agent data access

### Memory Management
- Automatic memory window cleanup
- Configurable memory size
- Context-aware task processing

### Task Tracking
- Full task lifecycle tracking
- Input/output data storage
- Status management

### Logging
- Activity logging
- Error tracking
- Performance monitoring

## 🔍 Testing Individual Agents

### Agent 1 (GPT-4) - Port 8001
```bash
# Test task execution
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"input_text": "What is the capital of France?", "task_type": "question"}'

# Get agent's tasks
curl http://localhost:8001/tasks

# Get agent's memory
curl http://localhost:8001/memory

# Get agent's configuration
curl http://localhost:8001/config

# Get agent's logs
curl http://localhost:8001/logs
```

### Agent 2 (Claude) - Port 8002
```bash
# Same endpoints as Agent 1, but on port 8002
curl http://localhost:8002/tasks
curl http://localhost:8002/memory
```

### Agent 3 (Llama) - Port 8003
```bash
# Same endpoints as Agent 1, but on port 8003
curl http://localhost:8003/tasks
curl http://localhost:8003/memory
```

## 🐳 Docker Configuration

### Environment Variables
Each agent gets:
- `MONGODB_URL`: Connection to its own database
- `AGENT_ID`: Unique agent identifier
- `HUB_URL`: Connection to main hub
- `OPENAI_API_KEY`: API key for AI models

### Volumes
Each agent has its own data volume:
- `agent1_data:/data/db` - Agent 1's MongoDB data
- `agent2_data:/data/db` - Agent 2's MongoDB data
- `agent3_data:/data/db` - Agent 3's MongoDB data

## 🔒 Security & Isolation

### Complete Isolation
- Each agent runs in its own container
- Each agent has its own database
- No shared data between agents
- Independent failure domains

### Data Persistence
- Each agent's data is persisted in its own volume
- Data survives container restarts
- No data loss between deployments

## 📊 Monitoring

### Health Checks
```bash
# Check if agents are running
docker-compose ps

# Check agent logs
docker-compose logs agent1
docker-compose logs agent2
docker-compose logs agent3
```

### Database Status
```bash
# Check MongoDB status in each agent
docker-compose exec agent1 mongosh --eval "db.runCommand('ping')"
docker-compose exec agent2 mongosh --eval "db.runCommand('ping')"
docker-compose exec agent3 mongosh --eval "db.runCommand('ping')"
```

## 🎉 Benefits

✅ **Complete Isolation**: Each agent is independent  
✅ **Lightweight**: Embedded MongoDB is much lighter than PostgreSQL  
✅ **Self-contained**: No external database dependencies  
✅ **Scalable**: Easy to add more agents  
✅ **Maintainable**: Shared code, separate data  
✅ **Fault Tolerant**: Agent failures don't affect others  

This architecture provides a robust, scalable, and maintainable system for AI agents with complete data isolation! 🚀
