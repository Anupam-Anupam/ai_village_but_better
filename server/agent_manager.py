"""
Agent Manager
=============
Manages agent processes - starts them on demand when tasks arrive.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

class AgentManager:
    """Manages agent lifecycle - starts and monitors agent processes."""

    def __init__(self):
        self.agents: Dict[str, Optional[subprocess.Popen]] = {
            "agent1-cua": None,
            "agent2-cua": None,
            "agent3-cua": None,
        }
        self.base_path = Path(__file__).parent.parent / "agents"
        self.agent_logs_dir = Path(__file__).parent.parent / "agent_logs"
        self.agent_logs_dir.mkdir(exist_ok=True)

    def is_agent_running(self, agent_id: str) -> bool:
        """Check if an agent process is running."""
        if agent_id not in self.agents or self.agents[agent_id] is None:
            return False

        # Check if process is still alive
        process = self.agents[agent_id]
        if process.poll() is not None:
            # Process has terminated
            self.agents[agent_id] = None
            return False

        return True

    def start_agent(self, agent_id: str) -> bool:
        """Start a single agent process."""
        if self.is_agent_running(agent_id):
            print(f"✓ Agent {agent_id} already running")
            return True

        agent_dir = self.base_path / agent_id
        main_file = agent_dir / "main.py"

        if not main_file.exists():
            print(f"✗ Agent {agent_id} main.py not found at {main_file}")
            return False

        try:
            # Set up environment
            env = os.environ.copy()
            env["AGENT_ID"] = agent_id

            # Log file for agent output
            log_file = self.agent_logs_dir / f"{agent_id}.log"
            log_handle = open(log_file, "a")

            # Start agent process
            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=str(agent_dir),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True  # Detach from parent
            )

            self.agents[agent_id] = process
            print(f"✓ Started agent {agent_id} (PID: {process.pid})")
            print(f"  Logs: {log_file}")

            # Give it a moment to start
            time.sleep(1)

            # Check if it's still running
            if process.poll() is not None:
                print(f"✗ Agent {agent_id} failed to start (check logs)")
                return False

            return True

        except Exception as e:
            print(f"✗ Failed to start agent {agent_id}: {e}")
            return False

    def start_all_agents(self):
        """Start all agents."""
        print("🤖 Starting all agents...")
        for agent_id in self.agents.keys():
            self.start_agent(agent_id)

        # Report status
        running = [aid for aid in self.agents.keys() if self.is_agent_running(aid)]
        print(f"✓ {len(running)}/{len(self.agents)} agents running")

    def stop_agent(self, agent_id: str):
        """Stop a single agent."""
        if not self.is_agent_running(agent_id):
            return

        try:
            process = self.agents[agent_id]
            process.terminate()
            process.wait(timeout=5)
            print(f"✓ Stopped agent {agent_id}")
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"✓ Killed agent {agent_id} (force)")
        except Exception as e:
            print(f"✗ Error stopping agent {agent_id}: {e}")
        finally:
            self.agents[agent_id] = None

    def stop_all_agents(self):
        """Stop all agents."""
        print("🛑 Stopping all agents...")
        for agent_id in self.agents.keys():
            self.stop_agent(agent_id)

    def get_status(self) -> dict:
        """Get status of all agents."""
        return {
            agent_id: "running" if self.is_agent_running(agent_id) else "stopped"
            for agent_id in self.agents.keys()
        }

    def ensure_agents_running(self):
        """Ensure at least one agent is running. Start agents if none are running."""
        running_agents = [aid for aid in self.agents.keys() if self.is_agent_running(aid)]

        if not running_agents:
            print("⚠️  No agents running, starting all agents...")
            self.start_all_agents()
        else:
            print(f"✓ {len(running_agents)} agent(s) already running")
