# 📊 Historial de Conversaciones - Documentación

## ⚠️ Solo para Desarrollo Local

**IMPORTANTE**: Este sistema de historial con SQLite **solo funciona en desarrollo local**. 

En Vercel (serverless), el historial está **deshabilitado por defecto** porque SQLite no persiste entre invocaciones. Los endpoints de historial retornarán error 503 en producción.

Para habilitar historial en producción, necesitas usar una base de datos externa como PostgreSQL (ver [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)).

---

## Descripción General

El sistema ahora incluye persistencia SQLite para almacenar todas las conversaciones y lecturas de sensores. Esto permite:

- **Tracking completo**: Todas las consultas (chat y sensores) se registran automáticamente
- **Análisis histórico**: Revisar conversaciones pasadas y patrones de uso
- **Estadísticas**: Métricas de uso, cultivos más consultados, tiempos de respuesta
- **Búsqueda**: Encontrar conversaciones anteriores por texto

## 🗄️ Base de Datos

### Ubicación
`./agriculture_history.db` (SQLite)

### Tablas

#### `chat_history`
Almacena todas las conversaciones (tanto de `/chat` como `/ask`):

```sql
- id (INTEGER, PK)
- timestamp (DATETIME)
- endpoint (VARCHAR) - "/v1/agro/chat" o "/v1/agro/ask"
- question (TEXT)
- crop (VARCHAR)
- stage (VARCHAR)
- parameter (VARCHAR)
- value (FLOAT)
- unit (VARCHAR)
- length (VARCHAR)
- answer (TEXT)
- model (VARCHAR)
- recommendation_json (JSON)
- response_time_ms (INTEGER)
- user_ip (VARCHAR)
- error (TEXT)
```

#### `sensor_readings`
Almacena específicamente las lecturas de sensores con sus recomendaciones:

```sql
- id (INTEGER, PK)
- timestamp (DATETIME)
- crop (VARCHAR)
- stage (VARCHAR)
- parameter (VARCHAR)
- value (FLOAT)
- unit (VARCHAR)
- action (VARCHAR) - "aumentar", "disminuir", "mantener"
- target_min (FLOAT)
- target_max (FLOAT)
- target_unit (VARCHAR)
- rationale (TEXT)
```

## 🔌 Nuevos Endpoints

### 1. GET `/v1/agro/history`
Obtiene el historial reciente de conversaciones.

**Query Parameters:**
- `limit` (int, default=50): Número máximo de resultados
- `endpoint` (string, opcional): Filtrar por endpoint (`/v1/agro/chat` o `/v1/agro/ask`)
- `crop` (string, opcional): Filtrar por cultivo

**Ejemplo:**
```powershell
# Últimas 20 conversaciones
curl http://localhost:8000/v1/agro/history?limit=20

# Solo conversaciones de chat
curl http://localhost:8000/v1/agro/history?endpoint=/v1/agro/chat

# Solo consultas sobre tomate
curl http://localhost:8000/v1/agro/history?crop=tomate
```

**Respuesta:**
```json
{
  "total": 15,
  "chats": [
    {
      "id": 42,
      "timestamp": "2025-11-29T21:30:00.123456",
      "endpoint": "/v1/agro/ask",
      "question": "¿Cómo afecta esta humedad?",
      "crop": "tomate",
      "stage": "floración",
      "parameter": "humedad_suelo",
      "value": 35.5,
      "unit": "%",
      "answer_preview": "La humedad actual (35.5%) está por debajo del rango óptimo...",
      "model": "gemini-2.5-flash",
      "response_time_ms": 520
    }
  ]
}
```

---

### 2. GET `/v1/agro/history/{chat_id}`
Obtiene el detalle completo de una conversación específica.

**Parámetros:**
- `chat_id` (int, path): ID de la conversación

**Ejemplo:**
```powershell
curl http://localhost:8000/v1/agro/history/42
```

**Respuesta:**
```json
{
  "id": 42,
  "timestamp": "2025-11-29T21:30:00.123456",
  "endpoint": "/v1/agro/ask",
  "question": "¿Cómo afecta esta humedad?",
  "crop": "tomate",
  "stage": "floración",
  "parameter": "humedad_suelo",
  "value": 35.5,
  "unit": "%",
  "length": "medium",
  "answer": "La humedad del suelo actual (35.5%) está por debajo del rango óptimo...",
  "model": "gemini-2.5-flash",
  "recommendation": {
    "action": "aumentar",
    "parameter": "humedad_suelo",
    "target_range": {
      "min": 60.0,
      "max": 80.0,
      "unit": "%"
    },
    "rationale": "Durante la etapa de floración...",
    "warnings": []
  },
  "response_time_ms": 520,
  "user_ip": "192.168.1.100",
  "error": null
}
```

---

### 3. GET `/v1/agro/sensors/history`
Obtiene el historial de lecturas de sensores con sus recomendaciones.

**Query Parameters:**
- `crop` (string, opcional): Filtrar por cultivo
- `parameter` (string, opcional): Filtrar por parámetro (ej: "humedad_suelo")
- `hours` (int, default=24): Últimas N horas
- `limit` (int, default=100): Número máximo de resultados

**Ejemplo:**
```powershell
# Últimas 24 horas de sensores
curl http://localhost:8000/v1/agro/sensors/history

# Humedad del suelo de tomate (últimas 48 horas)
curl "http://localhost:8000/v1/agro/sensors/history?crop=tomate&parameter=humedad_suelo&hours=48"
```

**Respuesta:**
```json
{
  "total": 8,
  "readings": [
    {
      "id": 15,
      "timestamp": "2025-11-29T20:15:00",
      "crop": "tomate",
      "stage": "floración",
      "parameter": "humedad_suelo",
      "value": 35.5,
      "unit": "%",
      "action": "aumentar",
      "target_range": {
        "min": 60.0,
        "max": 80.0,
        "unit": "%"
      },
      "rationale": "La humedad está por debajo del rango óptimo..."
    }
  ]
}
```

---

### 4. GET `/v1/agro/stats`
Obtiene estadísticas de uso del API.

**Ejemplo:**
```powershell
curl http://localhost:8000/v1/agro/stats
```

**Respuesta:**
```json
{
  "total_conversations": 245,
  "total_sensor_readings": 156,
  "top_crops": [
    {"crop": "tomate", "count": 89},
    {"crop": "maíz", "count": 67},
    {"crop": "lechuga", "count": 45}
  ],
  "top_parameters": [
    {"parameter": "humedad_suelo", "count": 78},
    {"parameter": "temperatura_aire", "count": 45},
    {"parameter": "ph_suelo", "count": 23}
  ],
  "avg_response_time_ms": 485.32
}
```

---

### 5. GET `/v1/agro/search`
Busca en el historial de conversaciones por texto.

**Query Parameters:**
- `q` (string, requerido): Término de búsqueda (mínimo 2 caracteres)
- `limit` (int, default=20): Número máximo de resultados

**Ejemplo:**
```powershell
# Buscar conversaciones sobre riego
curl "http://localhost:8000/v1/agro/search?q=riego&limit=10"

# Buscar por cultivo
curl "http://localhost:8000/v1/agro/search?q=tomate"
```

**Respuesta:**
```json
{
  "query": "riego",
  "total": 12,
  "results": [
    {
      "id": 78,
      "timestamp": "2025-11-29T19:45:00",
      "endpoint": "/v1/agro/chat",
      "question": "¿Cómo optimizar el riego en tomate?",
      "crop": "tomate",
      "answer_preview": "Para optimizar el riego del tomate, es fundamental considerar la etapa fenológica y las condiciones del suelo...",
      "response_time_ms": 450
    }
  ]
}
```

## 🧪 Testing Local

### 1. Inicializar la base de datos
```powershell
# La base de datos se inicializa automáticamente al arrancar el servidor
C:/Users/CORSAIR/Documents/GitHub/AI-API/.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

### 2. Generar datos de prueba
```powershell
# Ejecutar el script de prueba
C:/Users/CORSAIR/Documents/GitHub/AI-API/.venv/Scripts/python.exe scripts/test_database.py
```

### 3. Hacer consultas
```powershell
# Chat de texto
curl -X POST http://localhost:8000/v1/agro/chat `
  -H "Content-Type: application/json" `
  -d '{"question":"¿Cómo regar el tomate?","crop":"tomate","stage":"floración"}'

# Consulta con sensor
curl -X POST http://localhost:8000/v1/agro/ask `
  -H "Content-Type: application/json" `
  -d '{"parameter":"humedad_suelo","value":35.5,"unit":"%","crop":"tomate","stage":"floración"}'

# Ver historial
curl http://localhost:8000/v1/agro/history?limit=5

# Ver estadísticas
curl http://localhost:8000/v1/agro/stats

# Buscar
curl "http://localhost:8000/v1/agro/search?q=tomate"
```

## 🔒 Consideraciones

### Performance
- SQLite es adecuado para demos locales (hasta ~100K registros)
- Para producción con alto tráfico, considerar PostgreSQL/MySQL

### Privacidad
- Se almacena `user_ip` para análisis básicos
- No se almacenan datos personales identificables
- Considerar GDPR/CCPA si se despliega públicamente

### Mantenimiento
- La base de datos crece con el tiempo
- Implementar limpieza periódica si es necesario:
  ```python
  # Borrar conversaciones antiguas (ej: más de 30 días)
  from datetime import datetime, timedelta
  cutoff = datetime.utcnow() - timedelta(days=30)
  db.query(ChatHistory).filter(ChatHistory.timestamp < cutoff).delete()
  db.commit()
  ```

## 🎯 Casos de Uso

### 1. Panel de Administración
Usar `/stats` para dashboard en tiempo real con métricas de uso.

### 2. Análisis de Patrones
Usar `/sensors/history` para graficar tendencias de parámetros por cultivo.

### 3. Soporte al Usuario
Usar `/history/{chat_id}` para revisar conversaciones específicas si hay reportes de errores.

### 4. Búsqueda de Contexto
Usar `/search` para encontrar respuestas anteriores a preguntas similares.

### 5. Exportación de Datos
```python
# Ejemplo de exportación a CSV
import csv
from app.db.database import get_db, ChatHistory

db = next(get_db())
chats = db.query(ChatHistory).all()

with open('export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'endpoint', 'question', 'crop', 'answer'])
    for chat in chats:
        writer.writerow([chat.timestamp, chat.endpoint, chat.question, chat.crop, chat.answer])
```

## 📝 Notas Adicionales

- Todos los endpoints de lectura (`GET`) no requieren autenticación
- Los endpoints de escritura (`POST` para `/chat` y `/ask`) registran automáticamente en la base de datos
- Si el guardado en base de datos falla, no afecta la respuesta al usuario (failsafe)
- Los timestamps están en UTC
- La búsqueda es case-insensitive
