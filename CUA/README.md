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
