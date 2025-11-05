# Chat Interface API Documentation

The server now includes a full chat interface backend that allows users and agents to communicate through a chat-like system.

## Core Chat Endpoints

### POST `/chat/send`
Send a chat message. User messages automatically create tasks and broadcast to all agents.

**Request Body:**
```json
{
  "sender": "user",  // "user" or agent_id like "agent1", "agent2", "agent3"
  "message": "What is the derivative of 4x^3 + 3x^2 + pi?",
  "reply_to": null,  // Optional: message ID to reply to
  "metadata": {}     // Optional: additional data
}
```

**Response:**
```json
{
  "message_id": "msg_1234567890_0",
  "sender": "user",
  "message": "What is the derivative of 4x^3 + 3x^2 + pi?",
  "timestamp": "2025-01-XX...",
  "status": "sent",
  "task_id": "task_1234567890_0",  // Only if sender is "user"
  "agents_notified": 3  // Only if sender is "user"
}
```

**Behavior:**
- If `sender` is `"user"`: Creates a task, adds to task queue, broadcasts to all agents
- If `sender` is an agent: Stores message, available to user and other agents

### GET `/chat/history`
Get chat history in chronological order.

**Query Parameters:**
- `limit` (int, default 50): Number of messages to return
- `before` (string, optional): Get messages before this message_id (for pagination)

**Response:**
```json
{
  "messages": [
    {
      "message_id": "msg_123...",
      "sender": "user",
      "message": "Hello agents!",
      "timestamp": "2025-01-XX...",
      "reply_to": null,
      "metadata": {}
    },
    {
      "message_id": "msg_124...",
      "sender": "agent1",
      "message": "Hello! I received your message.",
      "timestamp": "2025-01-XX...",
      "reply_to": null,
      "metadata": {}
    }
  ],
  "count": 2,
  "has_more": false
}
```

### POST `/chat/reply`
Reply to a specific chat message (creates threaded conversation).

**Request Body:**
```json
{
  "sender": "agent1",
  "message": "I can help with that!",
  "reply_to": "msg_1234567890_0",  // Required: message ID to reply to
  "metadata": {}
}
```

### GET `/chat/messages/{message_id}`
Get a specific chat message by ID.

### POST `/chat/messages/{message_id}/read`
Mark a message as read by a specific reader.

**Request Body:**
```json
{
  "reader": "agent1"  // or "user"
}
```

### GET `/chat/participants`
Get all participants in the chat (user + all agents).

**Response:**
```json
{
  "participants": [
    {
      "id": "user",
      "type": "user",
      "message_count": 10,
      "status": "active"
    },
    {
      "id": "agent1",
      "type": "agent",
      "message_count": 5,
      "status": "online",
      "capabilities": ["computer_use", "web_automation"]
    }
  ],
  "total": 4
}
```

### GET `/chat/stats`
Get chat statistics.

**Response:**
```json
{
  "total_messages": 50,
  "user_messages": 20,
  "agent_messages": 30,
  "most_active": [
    {"sender": "agent1", "count": 15},
    {"sender": "user", "count": 20}
  ],
  "registered_agents": 3,
  "pending_tasks": 2
}
```

## Usage Examples

### User sends a message (creates task automatically):
```bash
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "user",
    "message": "What is the derivative of 4x^3 + 3x^2 + pi?"
  }'
```

### Agent sends a message:
```bash
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "agent1",
    "message": "I can help with that calculation!",
    "metadata": {"task_id": "task_123"}
  }'
```

### Get chat history:
```bash
curl http://localhost:8000/chat/history?limit=20
```

### Reply to a message:
```bash
curl -X POST http://localhost:8000/chat/reply \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "agent2",
    "message": "I agree with agent1",
    "reply_to": "msg_1234567890_1"
  }'
```

## Integration with Task System

- User messages automatically create tasks
- Tasks are linked to chat messages via `chat_message_id`
- Agents receive chat messages through their `/message` endpoint
- Agents can send chat messages using `/chat/send` with their agent_id as sender

## Database Schema

Chat messages are stored in MongoDB collection `chat_messages` with:
- `message_id`: Unique identifier
- `sender`: "user" or agent_id
- `message`: Message text
- `reply_to`: Optional parent message_id
- `metadata`: Optional additional data
- `timestamp`: When message was sent
- `read_by`: Array of who has read the message

