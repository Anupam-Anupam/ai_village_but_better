import subprocess
import os
import json
import base64
from typing import Dict
import re
from datetime import datetime

# Working directory inside container
WORKDIR = "/home/agent1/workdir"
os.makedirs(WORKDIR, exist_ok=True)

# Allowed commands whitelist
ALLOWED_CMDS = {"echo", "ls", "cat", "head", "tail", "uname", "date", "nano", "gedit"}

def execute_command(command: str) -> Dict[str, str]:
    """
    Safely execute shell commands with subprocess.
    Returns: {"status": "success/error", "message": "...", "output": "..."}
    """
    if not command.strip():
        return {"status": "error", "message": "empty command", "output": ""}
    
    # Basic security checks
    dangerous_chars = re.compile(r"[;&|`$><]")
    if dangerous_chars.search(command):
        return {"status": "error", "message": "forbidden characters", "output": ""}
    
    # Parse command safely
    try:
        parts = command.split()
        if not parts:
            return {"status": "error", "message": "no command found", "output": ""}
        
        exe = parts[0]
        if exe not in ALLOWED_CMDS:
            return {"status": "error", "message": f"command not allowed: {exe}", "output": ""}
        
        # Execute with timeout
        result = subprocess.run(
            [exe] + parts[1:],
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False
        )
        
        return {
            "status": "success",
            "message": "command executed",
            "output": result.stdout,
            "error": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "command timeout", "output": ""}
    except Exception as e:
        return {"status": "error", "message": f"execution error: {e}", "output": ""}

def generate_file(filename: str, content: str) -> Dict[str, str]:
    """
    Write text files to /home/agent1/workdir/ and return full path.
    Returns: {"status": "success/error", "message": "...", "path": "..."}
    """
    # Validate filename
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return {"status": "error", "message": "invalid filename", "path": ""}
    
    if not re.match(r"^[A-Za-z0-9._-]+$", filename):
        return {"status": "error", "message": "filename contains forbidden characters", "path": ""}
    
    # Ensure content is not too large
    if len(content.encode('utf-8')) > 16384:
        return {"status": "error", "message": "content too large", "path": ""}
    
    try:
        filepath = os.path.join(WORKDIR, filename)
        
        # Write file atomically
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, filepath)
        
        # Set restrictive permissions
        os.chmod(filepath, 0o600)
        
        return {
            "status": "success",
            "message": f"file written: {filename}",
            "path": filepath
        }
        
    except Exception as e:
        return {"status": "error", "message": f"write error: {e}", "path": ""}

def capture_screenshot(filepath: str) -> Dict[str, str]:
    """
    Take a screenshot using Playwright and save to /home/agent1/workdir/screenshots/.
    Returns: {"status": "success/error", "message": "...", "screenshot_path": "..."}
    """
    try:
        # Create screenshots directory
        screenshots_dir = os.path.join(WORKDIR, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Read file content
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Create HTML wrapper
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: monospace; white-space: pre-wrap; padding: 16px; }}
            </style>
        </head>
        <body>
            <pre>{content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</pre>
        </body>
        </html>
        """
        
        # Use Playwright for screenshot
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 900, "height": 600})
            page.set_content(html_content)
            
            # Generate screenshot filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"screenshot_{timestamp}.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
            
            page.screenshot(path=screenshot_path, full_page=True)
            browser.close()
        
        return {
            "status": "success",
            "message": "screenshot captured",
            "screenshot_path": screenshot_path
        }
        
    except Exception as e:
        return {"status": "error", "message": f"screenshot error: {e}", "screenshot_path": ""}

def handle_task(data: dict) -> Dict[str, str]:
    """
    Main entrypoint called by /execute; parses JSON input and decides action.
    Returns: {"status": "success/error", "message": "...", "result": "..."}
    """
    try:
        task_type = data.get("type", "")
        
        if task_type == "shell":
            command = data.get("command", "")
            return execute_command(command)
        
        elif task_type == "write":
            filename = data.get("filename", "")
            content = data.get("content", "")
            return generate_file(filename, content)
        
        elif task_type == "generate":
            filename = data.get("filename", "")
            instruction = data.get("instruction", "")
            
            # Use the AI-powered generate_file function instead of hardcoded templates
            return generate_file(filename, instruction)
        
        elif task_type == "screenshot":
            filepath = data.get("filepath", "")
            return capture_screenshot(filepath)
        
        else:
            return {"status": "error", "message": f"unknown task type: {task_type}", "result": ""}
    
    except Exception as e:
        return {"status": "error", "message": f"task handling error: {e}", "result": ""}

# Async wrapper functions for FastAPI compatibility
async def run_shell_command(command: str) -> Dict[str, str]:
    result = execute_command(command)
    return {"stdout": result.get("output", ""), "stderr": result.get("error", ""), "status": "ok" if result["status"] == "success" else "error"}

async def write_file(filename: str, content: str) -> Dict[str, str]:
    result = _write_file_sync(filename, content)
    return {"stdout": f"wrote {filename}", "stderr": "", "status": "ok" if result["status"] == "success" else "error"}

async def generate_file(filename: str, instruction: str) -> Dict[str, str]:
    """
    Generate file content from instruction using GPT-4 for real AI-powered content generation.
    """
    try:
        # Import OpenAI client
        from openai import OpenAI
        
        # Get API key from environment and clean it
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()  # Remove any whitespace/newlines
        if not api_key:
            # No API key available - return error instead of template
            return {"stdout": "", "stderr": "OpenAI API key not found. Cannot generate content.", "status": "error"}
        else:
            client = OpenAI(api_key=api_key)
            
            # Build context-aware prompt based on file type and instruction
            if filename.lower().endswith(".txt") or "story" in instruction.lower():
                system_prompt = "You are a creative writing assistant. Generate engaging, original content based on the user's specific instructions."
                user_prompt = f"Create content for file '{filename}'. Instruction: {instruction}"
            elif filename.lower().endswith(".py"):
                system_prompt = "You are a Python programming assistant. Generate clean, functional Python code based on the user's requirements."
                user_prompt = f"Create Python code for file '{filename}'. Instruction: {instruction}"
            else:
                system_prompt = "You are a helpful assistant. Generate appropriate content for the requested file based on the user's instructions."
                user_prompt = f"Create content for file '{filename}'. Instruction: {instruction}"
            
            # Generate content with GPT-4
            completion = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7  # Add some creativity/variation
            )
            
            content = completion.choices[0].message.content
            
            # Ensure content is not empty
            if not content or not content.strip():
                raise ValueError("Generated content is empty")
            
            # Use the synchronous file writer
            result = _write_file_sync(filename, content)
            return {"stdout": f"wrote {filename}", "stderr": "", "status": "ok" if result["status"] == "success" else "error"}
    
    except Exception as e:
        # Return error instead of template if AI generation fails
        return {"stdout": "", "stderr": f"AI generation failed: {str(e)}", "status": "error"}

def _write_file_sync(filename: str, content: str) -> Dict[str, str]:
    """Internal synchronous file writer"""
    # Validate filename
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return {"status": "error", "message": "invalid filename", "path": ""}
    
    if not re.match(r"^[A-Za-z0-9._-]+$", filename):
        return {"status": "error", "message": "filename contains forbidden characters", "path": ""}
    
    if len(content.encode('utf-8')) > 16384:
        return {"status": "error", "message": "content too large", "path": ""}
    
    try:
        filepath = os.path.join(WORKDIR, filename)
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, filepath)
        os.chmod(filepath, 0o600)
        
        return {"status": "success", "message": f"file written: {filename}", "path": filepath}
    except Exception as e:
        return {"status": "error", "message": f"write error: {e}", "path": ""}

async def read_file(filename: str) -> Dict[str, str]:
    try:
        filepath = os.path.join(WORKDIR, filename)
        if not os.path.exists(filepath):
            return {"stdout": "", "stderr": "file not found", "status": "not_found"}
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {"stdout": content, "stderr": "", "status": "ok"}
    except Exception as e:
        return {"stdout": "", "stderr": f"read error: {e}", "status": "error"}

async def browse_url(url: str) -> Dict[str, str]:
    return {"stdout": "", "stderr": "browse not implemented", "status": "unavailable"}

async def render_file_screenshot(filename: str) -> Dict[str, str]:
    try:
        filepath = os.path.join(WORKDIR, filename)
        if not os.path.exists(filepath):
            return {"screenshot": "", "stderr": "file not found", "status": "not_found"}
        
        # Read file content
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Create HTML wrapper
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: monospace; white-space: pre-wrap; padding: 16px; }}
            </style>
        </head>
        <body>
            <pre>{content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</pre>
        </body>
        </html>
        """
        
        # Use Playwright for screenshot
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 900, "height": 600})
            await page.set_content(html_content)
            
            png_bytes = await page.screenshot(type="png", full_page=True)
            await browser.close()
        
        b64_screenshot = base64.b64encode(png_bytes).decode("ascii")
        return {"screenshot": b64_screenshot, "stderr": "", "status": "ok"}
        
    except Exception as e:
        return {"screenshot": "", "stderr": f"render error: {e}", "status": "error"}