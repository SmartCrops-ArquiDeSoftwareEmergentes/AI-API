from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini_client import GeminiClient

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "agriculture_system_prompt.md"


@router.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "mock_mode": settings.mock_mode, "model": settings.gemini_model}


@router.post("/v1/agro/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """
    Endpoint principal para recomendaciones agrícolas.
    
    - Con datos de sensores (parameter + value): devuelve recomendación estructurada.
    - Solo con pregunta: devuelve respuesta educativa.
    """
    settings = get_settings()

    # Validación flexible: requiere 'question' o (parameter y value)
    has_question = bool(req.question and req.question.strip())
    has_measure = bool(req.parameter and (req.value is not None))
    if not has_question and not has_measure:
        raise HTTPException(status_code=400, detail="Debes enviar 'question' o bien 'parameter' y 'value'.")
    if has_question and len(req.question) > settings.max_input_chars:
        raise HTTPException(status_code=400, detail="La pregunta es demasiado larga.")

    try:
        client = GeminiClient(prompt_path=PROMPT_PATH)
        resp = client.ask(req)
        return resp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=502, detail="Error al consultar el modelo.") from e


@router.post("/v1/agro/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Endpoint simplificado para consultas de texto libre (sin datos de sensores).
    
    El usuario solo envía una pregunta en lenguaje natural y recibe una respuesta educativa.
    Ideal para casos de uso tipo chatbot o textbox en el frontend.
    """
    settings = get_settings()
    
    if len(req.question) > settings.max_input_chars:
        raise HTTPException(status_code=400, detail="La pregunta es demasiado larga.")
    
    try:
        client = GeminiClient(prompt_path=PROMPT_PATH)
        # Convertir ChatRequest a AskRequest para reutilizar la lógica existente
        ask_req = AskRequest(
            question=req.question,
            crop=req.crop,
            stage=req.stage,
            length=req.length,
            safe_mode=req.safe_mode
        )
        resp = client.ask(ask_req)
        
        # Convertir AskResponse a ChatResponse (solo campos relevantes)
        return ChatResponse(
            answer=resp.answer,
            model=resp.model,
            tips=resp.tips
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=502, detail="Error al consultar el modelo.") from e
