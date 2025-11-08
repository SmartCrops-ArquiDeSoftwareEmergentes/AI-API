from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict


class TargetRange(BaseModel):
    min: Optional[float] = Field(None, description="Valor mínimo orientativo del rango objetivo")
    max: Optional[float] = Field(None, description="Valor máximo orientativo del rango objetivo")
    unit: Optional[str] = Field(None, description="Unidad del rango objetivo")


class Recommendation(BaseModel):
    action: Optional[str] = Field(
        None,
        description="Acción sugerida: increase | decrease | maintain"
    )
    parameter: Optional[str] = Field(None, description="Nombre del parámetro evaluado")
    target_range: Optional[TargetRange] = Field(None, description="Rango orientativo para el parámetro")
    rationale: Optional[str] = Field(None, description="Breve justificación basada en el valor y el rango")
    warnings: Optional[List[str]] = Field(default=None, description="Lista de advertencias o supuestos")


class AskResponse(BaseModel):
    answer: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    tips: Optional[List[str]] = None
    recommendation: Optional[Recommendation] = Field(
        None,
        description="Objeto estructurado con acción direccional y justificación si se proporcionaron parámetros medibles."
    )
