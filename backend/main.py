import asyncio
import os
import socket
import json
from google import genai
from google.genai import types

from fastapi import FastAPI

import voice_parsing as vp

app = FastAPI()
control_lock = asyncio.Lock()

SYSTEM_PROMPT = """You are a wheelchair driver converting natural speech to precise instructions. 
You must output ONLY a JSON list of objects representing the sequence of movements.
Valid commands are: "movement_left", "movement_right", "movement_accelerate" (requires "duration" in seconds), "movement_reverse" (requires "duration" in seconds).
Assume 1 second durations when vague. Max duration is 10 seconds.

Example Output:
[
  {"name": "movement_accelerate", "args": {"duration": 2}},
  {"name": "movement_left", "args": {}}
]"""

genai_client = genai.Client()
chat = genai_client.chats.create(
    model="gemma-3-27b-it",
)


def send_to_bluetooth(message: str):
    host = "host.docker.internal"
    port = int(os.environ["BRIDGE_PORT"])

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))

            print(f"Sending: {message}")
            s.sendall(message.encode("utf-8"))

            # Keep reading until the Arduino sends a newline
            response = b""
            while b"\n" not in response:
                chunk = s.recv(1024)
                if not chunk:
                    break
                response += chunk

            print(
                f"Received from Bluetooth: {response.decode('utf-8', errors='replace').strip()}"
            )

    except ConnectionRefusedError:
        print("Error: Could not connect to the Windows Bridge. Is it running?")
    except socket.timeout:
        print("Error: Connection timed out.")


@app.post("/control")
async def _(prompt: str, use_ai: bool = False):
    if control_lock.locked():
        return {"error": "control already running"}
    
    print(f"Received {prompt=} {use_ai=}")

    async with control_lock:
        if not use_ai:
            instructions = vp.parse_speech(prompt)
            for move in instructions:
                print(f"Executing {move=}...")
            return dict(prompt=prompt, instructions=instructions)

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
        for cmd in commands:
            print(f"Executing {cmd['name']}...")

            if cmd["name"] == "movement_accelerate":
                send_to_bluetooth("W")
                await asyncio.sleep(int(cmd["args"]["duration"]))
                send_to_bluetooth("S")
            elif cmd["name"] == "movement_reverse":
                send_to_bluetooth("X")
                await asyncio.sleep(int(cmd["args"]["duration"]))
                send_to_bluetooth("S")
            elif cmd["name"] == "movement_left":
                send_to_bluetooth("L")
                await asyncio.sleep(2)
                send_to_bluetooth("S")
            elif cmd["name"] == "movement_right":
                send_to_bluetooth("R")
                await asyncio.sleep(2)
                send_to_bluetooth("S")
        return dict(prompt=prompt, instructions=final)
