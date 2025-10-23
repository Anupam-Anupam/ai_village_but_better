#!/usr/bin/env python3
"""
Agent Client for Docker containers to communicate with the hub
"""
import requests
import time
import json
import os

class AgentClient:
    def __init__(self, agent_id: int, hub_url: str = "http://localhost:8000"):
        self.agent_id = agent_id
        self.hub_url = hub_url
        self.container_id = os.getenv("HOSTNAME", "unknown")
        
    def register(self, memory_window_size: int = 10):
        """Register this agent with the hub"""
        response = requests.post(
            f"{self.hub_url}/agent/{self.agent_id}/register",
            json={
                "container_id": self.container_id,
                "memory_window_size": memory_window_size
            }
        )
        return response.json()
    
    def get_tasks(self):
        """Get pending tasks for this agent"""
        response = requests.get(f"{self.hub_url}/agent/{self.agent_id}/tasks")
        return response.json()
    
    def get_memory(self):
        """Get agent's memory window"""
        response = requests.get(f"{self.hub_url}/agent/{self.agent_id}/memory")
        return response.json()
    
    def add_memory(self, content: str, memory_type: str = "general", task_id: int = None):
        """Add a memory to agent's memory window"""
        data = {"content": content, "type": memory_type}
        if task_id:
            data["task_id"] = task_id
            
        response = requests.post(
            f"{self.hub_url}/agent/{self.agent_id}/memory",
            json=data
        )
        return response.json()
    
    def complete_task(self, task_id: int, output: str):
        """Mark a task as completed with output"""
        response = requests.post(
            f"{self.hub_url}/agent/{self.agent_id}/task/{task_id}/complete",
            json={"output": output}
        )
        return response.json()
    
    def run_agent_loop(self):
        """Main agent loop - continuously check for tasks and process them"""
        print(f"Agent {self.agent_id} starting...")
        
        # Register with hub
        self.register()
        print(f"Agent {self.agent_id} registered with container ID: {self.container_id}")
        
        while True:
            try:
                # Get pending tasks
                tasks_response = self.get_tasks()
                tasks = tasks_response.get("tasks", [])
                
                if tasks:
                    print(f"Found {len(tasks)} pending tasks")
                    
                    for task in tasks:
                        print(f"Processing task {task['id']}: {task['title']}")
                        
                        # Get memory for context
                        memory_response = self.get_memory()
                        memories = memory_response.get("memories", [])
                        
                        # Process task (this is where your AI logic would go)
                        result = self.process_task(task, memories)
                        
                        # Complete the task
                        self.complete_task(task["id"], result)
                        
                        # Add result to memory
                        self.add_memory(
                            f"Processed task: {task['title']} - Result: {result}",
                            "task_result",
                            task["id"]
                        )
                        
                        print(f"Completed task {task['id']}")
                else:
                    print("No pending tasks, waiting...")
                
                # Wait before checking again
                time.sleep(5)
                
            except Exception as e:
                print(f"Error in agent loop: {e}")
                time.sleep(10)
    
    def process_task(self, task: dict, memories: list) -> str:
        """
        Process a task - this is where you'd implement your AI logic
        Override this method in your agent implementation
        """
        # Simple example processing
        task_title = task.get("title", "Unknown task")
        input_data = task.get("input_data", {})
        
        # Use memory for context
        memory_context = "\n".join([m["content"] for m in memories[:3]])  # Use last 3 memories
        
        # Simple processing logic (replace with your AI)
        result = f"Processed '{task_title}' with input: {input_data}"
        if memory_context:
            result += f" (Context from memory: {memory_context[:100]}...)"
        
        return result

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent_client.py <agent_id> [hub_url]")
        sys.exit(1)
    
    agent_id = int(sys.argv[1])
    hub_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    client = AgentClient(agent_id, hub_url)
    client.run_agent_loop()
