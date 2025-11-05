# Automatic Agent Startup Implementation

## What Was Implemented

The chat server now automatically starts agents when a user sends a message through the chat interface.

## How It Works

1. **User sends message** → POST `/chat/messages` with `role: "user"`
2. **Server detects user message** → Checks if agents are running
3. **Agents auto-start** → If not running, starts all three agents (agent1-cua, agent2-cua, agent3-cua)
4. **Agents poll for tasks** → Agents continuously poll `/chat/tasks` every 5 seconds
5. **Agents process and respond** → When tasks are found, agents process them and post responses

## Implementation Details

### Server Changes (`server/main.py`)

- Added `start_agent()` function to start individual agent processes
- Added `start_all_agents_background()` to start all agents in a background thread
- Added `is_agent_running()` to check if agents are already running
- Modified `create_message()` to automatically start agents when user messages are received
- Added `/agents/status` endpoint to check agent status

### Agent Process Management

- Agents are started as subprocesses using `subprocess.Popen`
- Processes are detached using `start_new_session=True`
- Agent processes are tracked in `_running_agents` dictionary
- Thread-safe using `threading.Lock()`

## Usage

### Automatic Startup (Default)

Just send a message through the chat interface - agents will start automatically!

```bash
# No manual agent startup needed!
# Just send a message through the frontend
```

### Check Agent Status

```bash
curl http://localhost:8000/agents/status
```

Returns:
```json
{
  "agents": {
    "agent1-cua": {
      "running": true,
      "pid": 12345
    },
    "agent2-cua": {
      "running": true,
      "pid": 12346
    },
    "agent3-cua": {
      "running": true,
      "pid": 12347
    }
  }
}
```

## Requirements

1. **Server must be running** - Start with `./start_chat_server.sh`
2. **Agent directories must exist** - `agents/agent1-cua`, `agents/agent2-cua`, `agents/agent3-cua`
3. **Agent main.py files** - Each agent must have a `main.py` file
4. **Agent dependencies** - Agents need their required packages installed (CUA API keys, etc.)

## Troubleshooting

### Agents Don't Start

1. **Check server logs** - Look for errors in the server terminal
2. **Verify agent directories** - Ensure `agents/agent1-cua/main.py` exists
3. **Check agent dependencies** - Agents may fail if CUA_API_KEY or other env vars are missing
4. **Check agent status endpoint** - `curl http://localhost:8000/agents/status`

### Agents Start But Don't Process Tasks

1. **Verify agents are polling** - Check agent logs (if enabled)
2. **Check task endpoint** - `curl http://localhost:8000/chat/tasks?agent_id=agent1-cua`
3. **Verify agent environment** - Ensure `CHAT_SERVER_URL` and `AGENT_ID` are set

### Agents Crash Immediately

Agents may crash if:
- Missing required environment variables (CUA_API_KEY, OPENAI_API_KEY, etc.)
- Missing Python dependencies
- Invalid agent code

Check server logs for detailed error messages.

## Notes

- Agents start automatically when the **first user message** is sent
- Agents continue running until the server stops or they crash
- If an agent crashes, it will not automatically restart (manual restart required)
- Agents poll for tasks every 5 seconds (configurable via `CHAT_POLL_INTERVAL`)

