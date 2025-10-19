from fastapi import FastAPI, Request
import httpx, asyncio

# -----------------------------
# CONFIGURATION
# -----------------------------

AGENT_URLS = {
    "gpt4": "http://localhost:8001/execute",
    "claude": "http://localhost:8002/execute",
    "llama": "http://localhost:8003/execute"
}

app = FastAPI()


# -----------------------------
# MAIN ROUTE: /dispatch
# -----------------------------

@app.post("/dispatch")
async def dispatch_task(req: Request):
    """
    Accepts a structured JSON task (already parsed by task_parser.py),
    sends it to all AI agents, and returns their responses.
    No ranking or judging — pure communication hub.
    """
    # The body from task_parser should already look like:
    # {
    #   "task_type": "...",
    #   "input_text": "...",
    #   "constraints": {...}
    # }

    task_payload = await req.json()

    # Step 1 — Send the parsed task to all agents concurrently
    async with httpx.AsyncClient() as client_http:
        tasks = [
            client_http.post(url, json=task_payload)
            for url in AGENT_URLS.values()
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Step 2 — Collect responses from each agent
    agent_outputs = {}
    for name, response in zip(AGENT_URLS.keys(), responses):
        if isinstance(response, Exception):
            agent_outputs[name] = {"error": str(response)}
        else:
            try:
                agent_outputs[name] = response.json()
            except Exception:
                agent_outputs[name] = {
                    "error": "Invalid JSON from agent",
                    "raw": response.text
                }

    return {
        "task_payload": task_payload,
        "agent_outputs": agent_outputs
    }