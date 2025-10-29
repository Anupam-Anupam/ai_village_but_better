# Agent Sandbox (minimal) — agent1

Folder structure
- agents/agent_sandbox/           -> this directory implements the sandbox for agent1
  - Dockerfile
  - requirements.txt
  - app/
    - main.py        -> FastAPI app exposing POST /execute
    - executor.py    -> Secure task executor (shell whitelist + optional Playwright)

What each file does
- Dockerfile: builds an Ubuntu 22.04 container for agent1, creates a non-root user `agent1`, installs Python deps, copies the app, and runs uvicorn. The agent runs in /home/agent1/workdir.
- requirements.txt: minimal Python dependencies (FastAPI, uvicorn, playwright optional).
- app/main.py: FastAPI endpoint POST /execute expecting JSON {"type":"shell"|"browse"|"write","command":..., "filename":..., "content":...}.
- app/executor.py: Executes allowed shell commands securely (no shell=True, whitelist, timeout), provides write/read helpers, and a guarded Playwright fetch example.

How to adapt for agent2/agent3
- Copy this directory to agents/agent2_sandbox and agents/agent3_sandbox.
- In each copy:
  - change Dockerfile user and workdir (agent2 -> /home/agent2/workdir, AGENT_ID=2, etc.)
  - update executor.WORKDIR to the matching /home/agentX/workdir.
  - rebuild images with unique names/ports as needed.

How to build and run (manual steps you will perform later)
1. Build:
   - docker build -t agent-sandbox:latest -f agents/agent_sandbox/Dockerfile .
2. (Optional) If you want Playwright browsing:
   - Run the built container once or install browsers during build by adding `RUN playwright install --with-deps` to the Dockerfile.
3. Run:
   - docker run --rm -p 8001:8001 --name agent-sandbox agent-sandbox:latest
4. Test:
   - POST to http://localhost:8001/execute with JSON:
     - {"type":"shell","command":"echo hello"}
     - {"type":"browse","command":"https://example.com"}

Security notes and mitigations (important)
- The executor enforces:
  - A small whitelist of allowed commands (echo, ls, cat, head, tail, uname, date).
  - No shell metacharacters permitted (no ; & | > etc).
  - No absolute path arguments are allowed to avoid touching arbitrary host FS.
  - Commands run as a non-root user and in a dedicated WORKDIR.
  - subprocess is called without shell=True and with a timeout.
- Additional mitigations to consider:
  - Run container with seccomp, AppArmor, or gVisor for stronger syscall restrictions.
  - Use Linux namespaces and cgroups (container runtime) to limit CPU/memory.
  - Mount the workdir as an empty volume or tmpfs to avoid exposing host files.
  - Use an intrusion detection or logging agent and strict network egress rules.
  - Keep whitelist minimal and implement per-agent RBAC in the hub.

How this sandbox fits into a larger multi-agent system
- Each agent runs this container and exposes /execute to a central hub.
- The hub dispatches tasks to agents over HTTP and aggregates results.
- The sandbox is intentionally restrictive: it provides controlled, auditable command execution and optional web fetching.
- To scale, run multiple agent containers, give each a unique identity, and let the hub orchestrate tasks and resource limits.

Next steps (suggested)
- Add authentication between hub and agents (mutual TLS or signed tokens).
- Add logging and telemetry to capture commands and outputs centrally.
- Replace or extend the whitelist with structured task types instead of free-form shell.
- Add CI checks and automated security scans for the container image.

