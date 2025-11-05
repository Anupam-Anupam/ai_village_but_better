# Cua Agent Template

Welcome! This template helps you get started with the **Cua SDK** - a powerful framework for building AI agents that can interact with computers and automate tasks.

**Note**: This template will walk through a **cloud** based run. If you want to change this to local, please visit the [Quickstart](https://docs.cua.ai/docs/quickstart-devs).

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

You can run the agent in three ways:

**Option 1: Direct run (recommended for beginners)**

```bash
uv run python main.py
```

**Option 2: Traditional virtual environment**

```bash
source .venv/bin/activate
python main.py
```

**Option 3: Docker container**

```bash
# Build the image (run from the agent-template directory)
docker build -t agent-template .

# Run the agent, loading environment variables from your local .env file
docker run --rm --env-file .env agent-template
```

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
