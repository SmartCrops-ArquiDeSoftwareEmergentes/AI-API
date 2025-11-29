"""
Servicios para gestión del historial de chats.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.db.database import ChatHistory, SensorReading


class HistoryService:
    """Servicio para gestionar historial de conversaciones."""

    @staticmethod
    def save_chat(
        db: Session,
        endpoint: str,
        question: Optional[str],
        crop: Optional[str],
        stage: Optional[str],
        parameter: Optional[str],
        value: Optional[float],
        unit: Optional[str],
        length: Optional[str],
        answer: str,
        model: str,
        recommendation: Optional[Dict[str, Any]],
        response_time_ms: Optional[int],
        user_ip: Optional[str],
        error: Optional[str] = None
    ) -> ChatHistory:
        """Guardar una conversación en el historial."""
        chat = ChatHistory(
            endpoint=endpoint,
            question=question,
            crop=crop,
            stage=stage,
            parameter=parameter,
            value=value,
            unit=unit,
            length=length,
            answer=answer,
            model=model,
            recommendation_json=recommendation,
            response_time_ms=response_time_ms,
            user_ip=user_ip,
            error=error
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def save_sensor_reading(
        db: Session,
        crop: str,
        parameter: str,
        value: float,
        unit: str,
        action: str,
        stage: Optional[str] = None,
        target_min: Optional[float] = None,
        target_max: Optional[float] = None,
        target_unit: Optional[str] = None,
        rationale: Optional[str] = None
    ) -> SensorReading:
        """Guardar lectura de sensor con su recomendación."""
        reading = SensorReading(
            crop=crop,
            stage=stage,
            parameter=parameter,
            value=value,
            unit=unit,
            action=action,
            target_min=target_min,
            target_max=target_max,
            target_unit=target_unit,
            rationale=rationale
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)
        return reading

    @staticmethod
    def get_recent_chats(db: Session, limit: int = 20, endpoint: Optional[str] = None) -> List[ChatHistory]:
        """Obtener conversaciones recientes."""
        query = db.query(ChatHistory).order_by(desc(ChatHistory.timestamp))
        if endpoint:
            query = query.filter(ChatHistory.endpoint == endpoint)
        return query.limit(limit).all()

    @staticmethod
    def get_chats_by_crop(db: Session, crop: str, limit: int = 20) -> List[ChatHistory]:
        """Obtener conversaciones de un cultivo específico."""
        return (
            db.query(ChatHistory)
            .filter(ChatHistory.crop == crop)
            .order_by(desc(ChatHistory.timestamp))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_sensor_history(
        db: Session,
        crop: Optional[str] = None,
        parameter: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[SensorReading]:
        """Obtener historial de sensores con filtros."""
        since = datetime.utcnow() - timedelta(hours=hours)
        query = db.query(SensorReading).filter(SensorReading.timestamp >= since)
        
        if crop:
            query = query.filter(SensorReading.crop == crop)
        if parameter:
            query = query.filter(SensorReading.parameter == parameter)
        
        return query.order_by(desc(SensorReading.timestamp)).limit(limit).all()

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        """Obtener estadísticas generales del uso."""
        total_chats = db.query(func.count(ChatHistory.id)).scalar()
        total_sensors = db.query(func.count(SensorReading.id)).scalar()
        
        # Top cultivos
        top_crops = (
            db.query(ChatHistory.crop, func.count(ChatHistory.id).label("count"))
            .filter(ChatHistory.crop.isnot(None))
            .group_by(ChatHistory.crop)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )
        
        # Top parámetros
        top_params = (
            db.query(SensorReading.parameter, func.count(SensorReading.id).label("count"))
            .group_by(SensorReading.parameter)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )
        
        # Promedio tiempo de respuesta
        avg_response_time = (
            db.query(func.avg(ChatHistory.response_time_ms))
            .filter(ChatHistory.response_time_ms.isnot(None))
            .scalar()
        )
        
        return {
            "total_conversations": total_chats,
            "total_sensor_readings": total_sensors,
            "top_crops": [{"crop": c, "count": count} for c, count in top_crops],
            "top_parameters": [{"parameter": p, "count": count} for p, count in top_params],
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None
        }

    @staticmethod
    def search_chats(
        db: Session,
        query: str,
        limit: int = 20
    ) -> List[ChatHistory]:
        """Buscar en el historial por texto."""
        search_pattern = f"%{query}%"
        return (
            db.query(ChatHistory)
            .filter(
                (ChatHistory.question.ilike(search_pattern)) |
                (ChatHistory.answer.ilike(search_pattern))
            )
            .order_by(desc(ChatHistory.timestamp))
            .limit(limit)
            .all()
        )
