import asyncio
import os
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

genai_client = genai.Client()
chat = genai_client.chats.create(
    model="gemini-2.5-flash-lite",
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                function_declarations=[
                    movement_left,
                    movement_right,
                    movement_accelerate,
                    movement_reverse,
                ]
            )
        ],
        system_instruction="You are a wheelchair driver. Use the movement tools to navigate the course. Assume reasonably short timeouts like 1 second when it is vague. I am using you to convert natural speech to precise instructions for my wheelchair project, adjust accordingly.",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
    ),
)


@app.get("/control")
async def _(prompt: str):
    if control_lock.locked():
        return {"error": "control already running"}

    async with control_lock:
        response = chat.send_message(prompt)
        final = []
        for fn in response.function_calls:
            args = ", ".join(f"{key}={val}" for key, val in fn.args.items())
            final.append(f"{fn.name}({args})")

        return dict(prompt=prompt, instructions=final)
