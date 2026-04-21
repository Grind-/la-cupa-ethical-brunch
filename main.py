from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

HTML = open(os.path.join(os.path.dirname(__file__), "templates/index.html")).read()

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML
