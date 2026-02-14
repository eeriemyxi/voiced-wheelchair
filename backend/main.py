import asyncio

from fastapi import FastAPI

app = FastAPI()
control_lock = asyncio.Lock()


@app.get("/control")
async def _(prompt: str):
    if control_lock.locked():
        return {"error": "control already running"}

    async with control_lock:
        return dict(prompt=prompt)
