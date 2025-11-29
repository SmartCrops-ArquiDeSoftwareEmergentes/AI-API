"""
Base de datos SQLite para historial de conversaciones.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from pathlib import Path

# Crear directorio para la base de datos si no existe
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "chat_history.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ChatHistory(Base):
    """Modelo para guardar el historial de conversaciones."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    endpoint = Column(String(50), index=True)  # "/v1/agro/chat" o "/v1/agro/ask"
    
    # Request data
    question = Column(Text, nullable=True)
    crop = Column(String(100), nullable=True, index=True)
    stage = Column(String(100), nullable=True)
    parameter = Column(String(100), nullable=True, index=True)
    value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    length = Column(String(20), nullable=True)
    
    # Response data
    answer = Column(Text)
    model = Column(String(100))
    recommendation_json = Column(JSON, nullable=True)  # Guardar recommendation como JSON
    
    # Metadata
    response_time_ms = Column(Integer, nullable=True)  # Tiempo de respuesta en ms
    user_ip = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)  # Si hubo error


class SensorReading(Base):
    """Modelo para guardar lecturas de sensores y sus recomendaciones."""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    crop = Column(String(100), index=True)
    stage = Column(String(100), nullable=True)
    parameter = Column(String(100), index=True)
    value = Column(Float)
    unit = Column(String(50))
    
    # Recommendation
    action = Column(String(50))  # aumentar, disminuir, mantener
    target_min = Column(Float, nullable=True)
    target_max = Column(Float, nullable=True)
    target_unit = Column(String(50), nullable=True)
    rationale = Column(Text, nullable=True)


def init_db():
    """Inicializar la base de datos creando las tablas."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para obtener sesión de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
