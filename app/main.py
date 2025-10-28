from __future__ import annotations

from fastapi import FastAPI

from app.routes.agro import router as agro_router

app = FastAPI(title="Agro Gemini API", version="0.1.0")

app.include_router(agro_router)


@app.get("/")
async def root():
    return {"name": "Agro Gemini API", "docs": "/docs"}
