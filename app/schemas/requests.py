from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal


class AskRequest(BaseModel):
    question: str = Field(..., description="Pregunta principal para el asistente agronómico")
    crop: Optional[str] = Field(None, description="Cultivo (opcional)")
    temperature: Optional[float] = Field(None, description="Temperatura ambiente en °C (opcional)")
    safe_mode: Optional[bool] = Field(True, description="Modo educativo seguro: fuerza redacción no prescriptiva y reintentos educativos si hay bloqueo")
    length: Optional[Literal["short", "medium"]] = Field(
        None,
        description="Control de longitud de salida: 'short' (muy conciso) o 'medium' (conciso). Si no se indica, se usa 'medium'.",
    )
