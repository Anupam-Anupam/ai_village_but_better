import os
from fastapi import FastAPI, Request, HTTPException
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from a .env file at startup
load_dotenv()

# --- CONFIGURATION ---
# The API key is passed via environment variable for security
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Please set it in your .env file or as an environment variable.")

client = OpenAI(api_key=API_KEY)
app = FastAPI()

@app.post("/execute")
async def execute_task(req: Request):
    """
    Receives a task, sends it to the GPT-4 API, and returns the result.
    """
    try:
        task_payload = await req.json()
        input_text = task_payload.get("input_text", "")

        # This is a simplified example. You can build a more complex prompt
        # using the task_type and constraints from the payload.
        completion = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant executing a task."},
                {"role": "user", "content": input_text}
            ]
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))