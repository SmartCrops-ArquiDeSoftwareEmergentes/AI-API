from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini_client import GeminiClient
from app.db.database import get_db, init_db, ChatHistory
from app.db.history_service import HistoryService

router = APIRouter()

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "agriculture_system_prompt.md"

# Inicializar DB al cargar el módulo (solo si está habilitado)
settings = get_settings()
if settings.enable_history:
    init_db()


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "mock_mode": settings.mock_mode,
        "model": settings.gemini_model,
        "history_enabled": settings.enable_history
    }


@router.post("/v1/agro/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint principal para recomendaciones agrícolas.
    
    - Con datos de sensores (parameter + value): devuelve recomendación estructurada.
    - Solo con pregunta: devuelve respuesta educativa.
    """
    settings = get_settings()
    start_time = datetime.utcnow()

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
        
        # Calcular tiempo de respuesta
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Guardar en historial (solo si está habilitado)
        if settings.enable_history:
            try:
                rec_dict = None
                if resp.recommendation:
                    rec_dict = {
                        "action": resp.recommendation.action,
                        "parameter": resp.recommendation.parameter,
                        "target_range": {
                            "min": resp.recommendation.target_range.min if resp.recommendation.target_range else None,
                            "max": resp.recommendation.target_range.max if resp.recommendation.target_range else None,
                            "unit": resp.recommendation.target_range.unit if resp.recommendation.target_range else None
                        } if resp.recommendation.target_range else None,
                        "rationale": resp.recommendation.rationale,
                        "warnings": resp.recommendation.warnings
                    }
                
                HistoryService.save_chat(
                    db=db,
                    endpoint="/v1/agro/ask",
                    question=req.question,
                    crop=req.crop,
                    stage=req.stage,
                    parameter=req.parameter,
                    value=req.value,
                    unit=req.unit,
                    length=req.length,
                    answer=resp.answer,
                    model=resp.model,
                    recommendation=rec_dict,
                    response_time_ms=response_time,
                    user_ip=request.client.host if request.client else None
                )
                
                # Si hay datos de sensor, guardar también en tabla de sensores
                if has_measure and resp.recommendation:
                    tr = resp.recommendation.target_range
                    HistoryService.save_sensor_reading(
                        db=db,
                        crop=req.crop or "desconocido",
                        stage=req.stage,
                        parameter=req.parameter,
                        value=req.value,
                        unit=req.unit,
                        action=resp.recommendation.action,
                        target_min=tr.min if tr else None,
                        target_max=tr.max if tr else None,
                        target_unit=tr.unit if tr else None,
                        rationale=resp.recommendation.rationale
                    )
            except Exception as e:
                # No fallar si el guardado falla, solo loggear
                print(f"Error guardando historial: {e}")
        
        return resp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=502, detail="Error al consultar el modelo.") from e


@router.post("/v1/agro/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint simplificado para consultas de texto libre (sin datos de sensores).
    
    El usuario solo envía una pregunta en lenguaje natural y recibe una respuesta educativa.
    Ideal para casos de uso tipo chatbot o textbox en el frontend.
    """
    settings = get_settings()
    start_time = datetime.utcnow()
    
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
        
        # Calcular tiempo de respuesta
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Guardar en historial (solo si está habilitado)
        if settings.enable_history:
            try:
                HistoryService.save_chat(
                    db=db,
                    endpoint="/v1/agro/chat",
                    question=req.question,
                    crop=req.crop,
                    stage=req.stage,
                    parameter=None,
                    value=None,
                    unit=None,
                    length=req.length,
                    answer=resp.answer,
                    model=resp.model,
                    recommendation=None,
                    response_time_ms=response_time,
                    user_ip=request.client.host if request.client else None
                )
            except Exception as e:
                # No fallar si el guardado falla, solo loggear
                print(f"Error guardando historial: {e}")
        
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


@router.get("/v1/agro/history")
async def get_history(
    limit: int = 50,
    endpoint: Optional[str] = None,
    crop: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial reciente de conversaciones.
    
    - limit: número máximo de resultados (default 50)
    - endpoint: filtrar por endpoint (/v1/agro/chat o /v1/agro/ask)
    - crop: filtrar por cultivo
    """
    settings = get_settings()
    if not settings.enable_history:
        raise HTTPException(status_code=503, detail="Historial deshabilitado en este entorno")
    
    try:
        if endpoint:
            chats = HistoryService.get_recent_chats(db, limit=limit, endpoint=endpoint)
        elif crop:
            chats = HistoryService.get_chats_by_crop(db, crop=crop, limit=limit)
        else:
            chats = HistoryService.get_recent_chats(db, limit=limit)
        
        return {
            "total": len(chats),
            "chats": [
                {
                    "id": chat.id,
                    "timestamp": chat.timestamp.isoformat(),
                    "endpoint": chat.endpoint,
                    "question": chat.question,
                    "crop": chat.crop,
                    "stage": chat.stage,
                    "parameter": chat.parameter,
                    "value": chat.value,
                    "unit": chat.unit,
                    "answer_preview": chat.answer[:100] + "..." if len(chat.answer) > 100 else chat.answer,
                    "model": chat.model,
                    "response_time_ms": chat.response_time_ms
                }
                for chat in chats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener historial: {str(e)}") from e


@router.get("/v1/agro/history/{chat_id}")
async def get_chat_detail(chat_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el detalle completo de una conversación específica.
    """
    settings = get_settings()
    if not settings.enable_history:
        raise HTTPException(status_code=503, detail="Historial deshabilitado en este entorno")
    
    try:
        chat = db.query(ChatHistory).filter_by(id=chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        return {
            "id": chat.id,
            "timestamp": chat.timestamp.isoformat(),
            "endpoint": chat.endpoint,
            "question": chat.question,
            "crop": chat.crop,
            "stage": chat.stage,
            "parameter": chat.parameter,
            "value": chat.value,
            "unit": chat.unit,
            "length": chat.length,
            "answer": chat.answer,
            "model": chat.model,
            "recommendation": chat.recommendation_json,
            "response_time_ms": chat.response_time_ms,
            "user_ip": chat.user_ip,
            "error": chat.error
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener detalle: {str(e)}") from e


@router.get("/v1/agro/sensors/history")
async def get_sensor_history(
    crop: Optional[str] = None,
    parameter: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de lecturas de sensores y recomendaciones.
    
    - crop: filtrar por cultivo
    - parameter: filtrar por parámetro (ej: "humedad_suelo")
    - hours: últimas N horas (default 24)
    - limit: número máximo de resultados (default 100)
    """
    settings = get_settings()
    if not settings.enable_history:
        raise HTTPException(status_code=503, detail="Historial deshabilitado en este entorno")
    
    try:
        sensors = HistoryService.get_sensor_history(
            db=db,
            crop=crop,
            parameter=parameter,
            hours=hours,
            limit=limit
        )
        
        return {
            "total": len(sensors),
            "readings": [
                {
                    "id": s.id,
                    "timestamp": s.timestamp.isoformat(),
                    "crop": s.crop,
                    "stage": s.stage,
                    "parameter": s.parameter,
                    "value": s.value,
                    "unit": s.unit,
                    "action": s.action,
                    "target_range": {
                        "min": s.target_min,
                        "max": s.target_max,
                        "unit": s.target_unit
                    } if s.target_min is not None or s.target_max is not None else None,
                    "rationale": s.rationale
                }
                for s in sensors
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener sensores: {str(e)}") from e


@router.get("/v1/agro/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas de uso del API.
    
    Retorna total de chats, total de sensores, cultivos más consultados,
    parámetros más medidos, y tiempo promedio de respuesta.
    """
    settings = get_settings()
    if not settings.enable_history:
        raise HTTPException(status_code=503, detail="Historial deshabilitado en este entorno")
    
    try:
        stats = HistoryService.get_stats(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}") from e


@router.get("/v1/agro/search")
async def search_history(
    q: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Busca en el historial de conversaciones por texto.
    
    - q: término de búsqueda (busca en preguntas y respuestas)
    - limit: número máximo de resultados (default 20)
    """
    settings = get_settings()
    if not settings.enable_history:
        raise HTTPException(status_code=503, detail="Historial deshabilitado en este entorno")
    
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="El término de búsqueda debe tener al menos 2 caracteres")
    
    try:
        chats = HistoryService.search_chats(db, query=q, limit=limit)
        
        return {
            "query": q,
            "total": len(chats),
            "results": [
                {
                    "id": chat.id,
                    "timestamp": chat.timestamp.isoformat(),
                    "endpoint": chat.endpoint,
                    "question": chat.question,
                    "crop": chat.crop,
                    "answer_preview": chat.answer[:150] + "..." if len(chat.answer) > 150 else chat.answer,
                    "response_time_ms": chat.response_time_ms
                }
                for chat in chats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}") from e
