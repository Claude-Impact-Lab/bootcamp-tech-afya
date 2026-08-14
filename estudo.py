"""Arquivo de estudo do tutorial do FastAPI.

Nao faz parte do projeto: e um rascunho para experimentar sem medo.
Rode com:

    uv run uvicorn estudo:app --reload --port 8001

E abra http://127.0.0.1:8001 (ou /docs para a documentacao automatica).
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
