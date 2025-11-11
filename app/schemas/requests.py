from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal


class AskRequest(BaseModel):
    question: Optional[str] = Field(None, description="Pregunta principal (opcional si se envía parámetro y valor)")
    crop: Optional[str] = Field(None, description="Cultivo (opcional)")
    temperature: Optional[float] = Field(None, description="Temperatura ambiente en °C (opcional)")
    safe_mode: Optional[bool] = Field(True, description="Modo educativo seguro: fuerza redacción no prescriptiva y reintentos educativos si hay bloqueo")
    length: Optional[Literal["short", "medium"]] = Field(
        None,
        description="Control de longitud de salida: 'short' (muy conciso) o 'medium' (conciso). Si no se indica, se usa 'medium'.",
    )
    # Campos opcionales para lecturas de sensores y ajustes dirigidos
    parameter: Optional[str] = Field(
        None,
        description="Nombre del parámetro medido (acepta español preferentemente y también inglés)."
    )
    value: Optional[float] = Field(
        None,
        description="Valor observado del parámetro (numérico)."
    )
    unit: Optional[str] = Field(
        None,
        description="Unidad del parámetro (p. ej., % , °C, dS/m, pH, mm, etc.)."
    )
    stage: Optional[str] = Field(
        None,
        description="Etapa fenológica (opcional), p. ej., V6, floración, cuaje, etc."
    )

    @classmethod
    def _map_parameter(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        mapping = {
            "humedad_suelo": "soil_moisture",
            "temperatura_aire": "air_temperature",
            "temperatura_suelo": "soil_temperature",
            "humedad_aire": "air_humidity",
            "ph_suelo": "soil_ph",
            "luz": "light",
            "lluvia": "rain",
            "nutrientes": "nutrients",
            # identidades/compat inglés
            "light": "light",
            "rain": "rain",
            "nutrients": "nutrients",
            "otro": "other",
            "other": "other",
        }
        return mapping.get(value, value)

    def model_post_init(self, __context):  # pydantic v2 hook
        # Normaliza a forma inglesa interna para la lógica del modelo, manteniendo el valor original disponible en output
        if self.parameter:
            object.__setattr__(self, "parameter", self._map_parameter(self.parameter))
