from fastapi import FastAPI, Request
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import re, json

app = FastAPI()

MODEL_NAME = "google/flan-t5-small"  # lightweight and open
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

@app.post("/parse")
async def parse_task(req: Request):
    data = await req.json()
    prompt = data.get("prompt", "")

    # Light instruction template for structured parsing
    instruction = (
        "Parse the following request into structured JSON fields: "
        "task_type, input_text, and constraints (if applicable). "
        "If no constraints are mentioned, leave constraints as {}. "
        f"Request: {prompt}"
    )

    inputs = tokenizer(instruction, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=128)
    raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # try to clean/ensure JSON format
    match = re.search(r"\{.*\}", raw_output, re.DOTALL)
    json_str = match.group(0) if match else None

    try:
        result = json.loads(json_str)
    except Exception:
        result = {
            "task_type": "unknown",
            "input_text": prompt,
            "constraints": {}
        }

    return result