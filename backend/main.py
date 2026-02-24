import asyncio
import os
import json
from google import genai
from google.genai import types

from fastapi import FastAPI

app = FastAPI()
control_lock = asyncio.Lock()

movement_left = {"name": "movement_left", "description": "Turn left by 90 degrees."}

movement_right = {"name": "movement_right", "description": "Turn right by 90 degrees."}

movement_accelerate = {
    "name": "movement_accelerate",
    "description": "Accelerate the wheelchair for N seconds.",
    "parameters": {
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "The number of seconds to accelerate for.",
            }
        },
    },
}

movement_reverse = {
    "name": "movement_reverse",
    "description": "Move the wheelchair backwards for N seconds.",
    "parameters": {
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "The number of seconds to reverse for.",
            }
        },
    },
}

SYSTEM_PROMPT = """You are a wheelchair driver converting natural speech to precise instructions. 
You must output ONLY a JSON list of objects representing the sequence of movements.
Valid commands are: "movement_left", "movement_right", "movement_accelerate" (requires "duration" in seconds), "movement_reverse" (requires "duration" in seconds).
Assume 1 second durations when vague.

Example Output:
[
  {"name": "movement_accelerate", "args": {"duration": 2}},
  {"name": "movement_left", "args": {}}
]"""

genai_client = genai.Client()
chat = genai_client.chats.create(
    model="gemma-3-27b-it",
)


@app.get("/control")
async def _(prompt: str):
    if control_lock.locked():
        return {"error": "control already running"}

    async with control_lock:
        response = chat.send_message(SYSTEM_PROMPT + f"---\nINPUT: " + prompt)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        commands = json.loads(clean_text)
        final = []
        for cmd in commands:
            args = ", ".join(f"{key}={val}" for key, val in cmd.get("args", {}).items())
            final.append(f"{cmd['name']}({args})")
        return dict(prompt=prompt, instructions=final)
