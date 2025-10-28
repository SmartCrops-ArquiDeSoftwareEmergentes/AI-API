from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse
from app.services.gemini_client import GeminiClient

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "agriculture_system_prompt.md"


@router.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "mock_mode": settings.mock_mode, "model": settings.gemini_model}


@router.post("/v1/agro/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    settings = get_settings()

    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Se requiere 'question'.")
    if len(req.question) > settings.max_input_chars:
        raise HTTPException(status_code=400, detail="La pregunta es demasiado larga.")

    try:
        client = GeminiClient(prompt_path=PROMPT_PATH)
        resp = client.ask(req)
        return resp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=502, detail="Error al consultar el modelo.") from e
