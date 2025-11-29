from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ChatRequest(BaseModel):
    """Esquema simplificado para consultas de texto libre sin datos de sensores."""
    question: str = Field(..., description="Pregunta o consulta en lenguaje natural sobre agricultura")
    crop: Optional[str] = Field(None, description="Cultivo (opcional)")
    stage: Optional[str] = Field(None, description="Etapa fenológica (opcional)")
    length: Optional[Literal["short", "medium"]] = Field(
        "medium",
        description="Control de longitud: 'short' (conciso) o 'medium' (detallado)"
    )
    safe_mode: Optional[bool] = Field(
        True,
        description="Modo educativo seguro con reframings automáticos"
    )


class ChatResponse(BaseModel):
    """Respuesta educativa para consultas de texto."""
    answer: str = Field(..., description="Respuesta educativa en formato texto o bullets")
    model: str = Field(..., description="Modelo usado para generar la respuesta")
    tips: Optional[list[str]] = Field(None, description="Tips adicionales opcionales")
