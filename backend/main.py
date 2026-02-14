from fastapi import FastAPI

app = FastAPI()

@app.get("/control")
def _(prompt: str):
    return dict(prompt=prompt)
