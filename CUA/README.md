# Cua Agent Template

Welcome! This template helps you get started with the **Cua SDK** - a powerful framework for building AI agents that can interact with computers and automate tasks.

**Note**: This template will walk through a **cloud** based run. If you want to change this to local, please visit the [Quickstart](https://docs.cua.ai/docs/quickstart-devs).

## Table of Contents

- [What does this template do?](#what-does-this-template-do)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Step 1: Set up your environment](#step-1-set-up-your-environment)
  - [Step 2: Run your first agent!](#step-2-run-your-first-agent-)
- [Docker Support](#-docker-support)
- [Installing uv](#-installing-uv-if-you-dont-have-it)
- [What's Next?](#-whats-next)
- [Troubleshooting](#-troubleshooting)

## What does this template do?

This example demonstrates how to use the **ComputerAgent** with OpenAI's computer-use model to:

- Automate web interactions (visiting websites, downloading files)
- Fill out forms automatically using information from documents
- Run tasks on a cloud-based Linux virtual machine

The agent can see your screen, control your mouse and keyboard, and make intelligent decisions about how to complete tasks - just like a human would!

## 🚀 Quick Start

### Prerequisites

Before you begin, you'll need:

- A **Cua account** and active sandbox
- An **OpenAI API key** with access to the computer-use model
- **uv** package manager (we'll help you install it if needed)

### Step 1: Set up your environment

1. **Clone this repository:**

   ```bash
   git clone https://github.com/trycua/agent-template.git
   cd agent-template
   ```

2. **Copy the environment template:**

   ```bash
   cp .env.example .env
   ```

3. **Start your virtual machine:**

   - Go to [Cua Dashboard](https://www.cua.ai/dashboard/sandboxes)
   - Make sure your sandbox is running (you'll see a green status indicator)

4. **Configure your API keys:**

   - Open the `.env` file in your favorite editor
   - Fill in your `CUA_API_KEY`, `CUA_SANDBOX_NAME`, and `OPENAI_API_KEY`
   - Save the file

5. **Install dependencies:**
   ```bash
   uv sync
   ```

### Step 2: Run your first agent! 🎉

You can run the agent in several ways:

**Option 1: Using Docker (recommended for production)**

```bash
# Quick setup
make setup

# Run with Docker Compose
make run

# Or run directly with Docker
make run-direct
```

**Option 2: Direct run with uv (recommended for development)**

```bash
uv run python main.py
```

**Option 3: Traditional virtual environment**

```bash
source .venv/bin/activate
python main.py
```

## 🐳 Docker Support

This template includes full Docker support for easy deployment and development:

- **Dockerfile**: Multi-stage build with all dependencies
- **docker-compose.yml**: Easy orchestration with volume mounts
- **Makefile**: Simple commands for common operations
- **DOCKER.md**: Comprehensive Docker documentation

### Quick Docker Start

```bash
# Setup environment and run
make setup
make run

# View logs
make logs

# Stop when done
make stop
```

For detailed Docker instructions, see [DOCKER.md](DOCKER.md).

## 📦 Installing uv (if you don't have it)

**macOS/Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**

```bash
pip install uv
```

## 🛠️ Customizing Your Agent

Want to try different models or tasks? Here are some ideas:

- **Switch models:** Check out [supported model providers](https://docs.cua.ai/docs/agent-sdk/supported-model-providers) for options like Claude, UI-TARS, or local models
- **Change tasks:** Modify the `tasks` list in `main.py` to automate different workflows
- **Local development:** Switch to a **free** local macOS computer for testing (see commented code in `main.py`), find resources on local development: https://docs.cua.ai/docs/quickstart-devs

## 🆘 Need Help?

We're here to help you succeed!

- 📚 **[Documentation](https://docs.cua.ai/docs)** - Comprehensive guides and examples
- 💬 **[Discord Community](https://discord.com/invite/mVnXXpdE85)** - Get support from our team and other developers
- 🔧 **[GitHub Repository](https://github.com/trycua/cua)** - Source code, issues, and contributions

## 🎯 What's Next?

Once you've got this example running, try:

- Building your own custom agents
- Integrating with your existing workflows
- Exploring advanced features like multi-agent systems
- Contributing to the open-source community

Happy automating, feel free to leave us a star if you liked this! 🚀

Project Overview

You are an expert full-stack engineer tasked with building the frontend for a multi-agent AI orchestration platform.
The backend (FastAPI, Python) is mostly complete, but not yet attached. You must ensure that the frontend is structured to integrate seamlessly once backend endpoints are finalized.

The backend manages:

Multiple containerized CUA-like agents running on Linux VMs

Agents send logs, progress, and screenshots to MongoDB, PostgreSQL, and MinIO

An Evaluator Agent produces graphs, performance metrics, and task overviews

A Hub coordinates user requests and agent tasks

You will now create a React + Vite + Tailwind + shadcn/ui frontend, inspired by AI Village and LMArena, focusing on simplicity, modularity, and future extensibility.

Functional Goals

UI/UX Goals

A live dashboard displaying:

Active agents and their task progress

Performance metrics from the Evaluator Agent (via graphs)

Real-time logs and task completion status

A Chat Interface where users can issue tasks or questions to agents.

A Leaderboard View (for multi-agent competition scenarios).

A Screenshot Viewer that displays the latest screenshots pulled from MinIO (via backend API).

Backend Integration (Future-Proofing)

The backend API endpoints are not yet attached.

You must index and inspect the backend codebase (search for route definitions, e.g., @app.get, @app.post, etc.) to identify how data will be fetched.

Create placeholder API calls and configuration in /src/api/ that can be easily bound later.

Ensure CORS and socket endpoints are anticipated for minimal refactoring later.

Tech Stack

Frontend Framework: React 19 + Vite

Styling: Tailwind CSS + shadcn/ui

State Management: Zustand

Charts: Recharts

Communication: Fetch + WebSocket (for future live updates)

Build Tool: Vite

Deployment: Docker-ready static build

Folder Structure (Required)
frontend/
├── src/
│   ├── components/
│   │   ├── ChatBox.jsx
│   │   ├── Leaderboard.jsx
│   │   ├── AgentCard.jsx
│   │   ├── ScoreGraph.jsx
│   │   ├── ScreenshotViewer.jsx
│   │   └── TaskFeed.jsx
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   └── Chat.jsx
│   ├── api/
│   │   ├── config.js          // Base URLs (backend endpoints placeholder)
│   │   ├── hubAPI.js          // Placeholder: fetch user requests and agent states
│   │   ├── evaluatorAPI.js    // Placeholder: fetch performance graphs
│   │   ├── agentAPI.js        // Placeholder: agent task logs and updates
│   ├── store/
│   │   └── useAgentStore.js   // Zustand global store
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── public/
│   └── favicon.ico
├── vite.config.js
└── Dockerfile

Implementation Requirements

1. Initialize the Project

Scaffold a Vite React project (npm create vite@latest frontend --template react).

Configure Tailwind and shadcn/ui.

Create minimal example components with placeholder data.

2. Inspect the Backend Codebase

Search for FastAPI route definitions (@app.get, @app.post, etc.).

Identify all existing endpoints that serve:

Agent logs

Evaluator metrics

User task submissions

MinIO media access

For each, define corresponding placeholder API handlers in /src/api/ that mock realistic data.

3. Build Reusable Components

AgentCard → Displays agent name, task progress, and health.

TaskFeed → Scrollable log of agent updates.

ScoreGraph → Uses Recharts to plot Evaluator Agent scores over time.

Leaderboard → Table view ranking agents by performance (if multiple agents exist).

ChatBox → Input/output interface for user-to-agent interaction (mock backend response for now).

ScreenshotViewer → Displays screenshots from a mocked MinIO URL list.

4. Global State (Zustand)

Store and manage:

Agents list

Active tasks

Evaluator metrics

Chat messages

Mock initial state and demonstrate UI updates.

5. Styling and Layout

Use Tailwind and shadcn/ui components.

Create a responsive layout:

+------------------------------------------------+
| Sidebar (Agents) |    Dashboard / Chat Area    |
+------------------------------------------------+
| Graphs / Logs / Screenshots                    |
+------------------------------------------------+


Dark theme default.

6. Documentation

Include README.md explaining:

Project structure

How to connect backend later

Where to update API endpoints

7. Dockerfile

Multi-stage Dockerfile to build and serve the React app with Nginx or Vite preview.

Important Constraints

Do not execute terminal commands directly; only show them in comments.

Use mock APIs but organize the code as if it were connected.

Keep all code minimal and modular — focus on scalability and readability.

The Cursor agent must index the backend folder before scaffolding to ensure seamless data shape compatibility (e.g., JSON schemas, routes, field names).

Deliverables

Fully scaffolded frontend codebase

Placeholder API integration ready to connect to FastAPI backend

Minimal Dockerfile

README explaining setup

Example dashboard populated with mock data

Example Next Step (Once Backend Ready)

When backend endpoints (FastAPI) are stable:

Replace mock API URLs in /src/api/config.js

Swap mock fetches with real axios or fetch calls

Add WebSocket integration for real-time updates

Final Note for Cursor Agent:
Before writing any code:

Index and inspect the backend directory.

Identify key endpoints (URLs, payload structure).

Then scaffold the frontend with mock API data that mirrors backend payloads.