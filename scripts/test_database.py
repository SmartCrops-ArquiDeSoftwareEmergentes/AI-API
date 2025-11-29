"""
Script de prueba para verificar la inicialización de la base de datos
y las operaciones básicas del historial de chats.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.db.database import init_db, get_db, ChatHistory, SensorReading
from app.db.history_service import HistoryService

def test_database():
    print("🔧 Inicializando base de datos...")
    init_db()
    print("✅ Base de datos inicializada")
    
    # Obtener sesión
    db = next(get_db())
    
    print("\n📊 Guardando chat de prueba...")
    HistoryService.save_chat(
        db=db,
        endpoint="/v1/agro/chat",
        question="¿Cómo regar el tomate?",
        crop="tomate",
        stage="floración",
        parameter=None,
        value=None,
        unit=None,
        length="medium",
        answer="El riego del tomate durante la floración requiere mantener humedad constante...",
        model="gemini-2.5-flash",
        recommendation=None,
        response_time_ms=450,
        user_ip="127.0.0.1"
    )
    print("✅ Chat guardado")
    
    print("\n📊 Guardando lectura de sensor...")
    HistoryService.save_sensor_reading(
        db=db,
        crop="tomate",
        stage="floración",
        parameter="humedad_suelo",
        value=35.5,
        unit="%",
        action="aumentar",
        target_min=60.0,
        target_max=80.0,
        target_unit="%",
        rationale="La humedad actual está por debajo del rango óptimo para la etapa de floración"
    )
    print("✅ Sensor guardado")
    
    print("\n📋 Obteniendo historial reciente...")
    chats = HistoryService.get_recent_chats(db, limit=10)
    print(f"✅ Encontrados {len(chats)} chats")
    for chat in chats:
        print(f"   - [{chat.timestamp}] {chat.endpoint}: {chat.question[:50]}...")
    
    print("\n📊 Obteniendo estadísticas...")
    stats = HistoryService.get_stats(db)
    print(f"✅ Total conversaciones: {stats['total_conversations']}")
    print(f"✅ Total sensores: {stats['total_sensor_readings']}")
    print(f"✅ Cultivos principales: {stats['top_crops']}")
    print(f"✅ Parámetros principales: {stats['top_parameters']}")
    print(f"✅ Tiempo promedio de respuesta: {stats['avg_response_time_ms']}ms")
    
    print("\n🔍 Probando búsqueda...")
    results = HistoryService.search_chats(db, query="tomate", limit=5)
    print(f"✅ Encontrados {len(results)} resultados para 'tomate'")
    
    db.close()
    print("\n✅ Todas las pruebas completadas exitosamente!")

if __name__ == "__main__":
    try:
        test_database()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
