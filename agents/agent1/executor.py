"""
Secure Task Executor for the AI Agent Sandbox.

Handles two types of commands:
1.  `shell`: Executes sandboxed shell commands.
2.  `browse`: Uses Playwright to fetch a web page's content.
"""
import subprocess
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright


async def execute_task(command_type: str, params: Dict[str, Any]) -> Dict[str, str]:
    """
    Routes the task to the appropriate executor based on command_type.

    Args:
        command_type: The type of command ('shell' or 'browse').
        params: A dictionary of parameters for the command.

    Returns:
        A dictionary containing stdout, stderr, and an optional error message.
    """
    if command_type == "shell":
        return await run_shell_command(params.get("command", ""))
    elif command_type == "browse":
        return await browse_web(params.get("url", ""))
    else:
        return {"stdout": "", "stderr": f"Unknown command type: {command_type}"}


async def run_shell_command(command: str) -> Dict[str, str]:
    """
    Executes a shell command in a sandboxed manner.

    Security:
    - Runs as a non-root user (defined in Dockerfile).
    - `shell=False` prevents shell injection vulnerabilities. The command is
      split into a list, so it's treated as a program and its arguments.
    """
    if not command:
        return {"stdout": "", "stderr": "No command provided."}

    try:
        # Split the command into a list to avoid shell injection
        args = command.split()
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return {"stdout": stdout.decode(), "stderr": stderr.decode()}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"Command not found: {command.split()[0]}"}
    except Exception as e:
        return {"stdout": "", "stderr": f"Error executing command: {str(e)}"}


async def browse_web(url: str) -> Dict[str, str]:
    """Uses Playwright to fetch the text content of a URL."""
    if not url:
        return {"stdout": "", "stderr": "No URL provided."}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            content = await page.content()
            await browser.close()
            # For simplicity, we return the full HTML. An agent could parse this.
            return {"stdout": content, "stderr": ""}
    except Exception as e:
        return {"stdout": "", "stderr": f"Error browsing URL '{url}': {str(e)}"}