# Agro Gemini API

Una API en FastAPI que envuelve Google Gemini con un prompt de experto en agricultura para entregar recomendaciones prácticas basadas en los datos proporcionados.

## Requisitos
- Python 3.10+
- Una clave de API de Gemini (opcional para modo demo). Crea una en https://ai.google.dev/ si deseas respuestas reales.

## Configuración (Windows PowerShell)

```powershell
# 1) Crear entorno virtual
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) Configurar variables de entorno
Copy-Item .env.example .env
# Edita .env y coloca tu clave en GEMINI_API_KEY. Deja MOCK_MODE=true si quieres modo demo.

# 4) Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

Abre http://127.0.0.1:8000/docs para probar desde Swagger UI.

## Endpoints
- GET `/health` -> Estado del servicio, modelo y si está en modo demo.
- POST `/v1/agro/ask` -> Pregunta con contexto agrícola y datos. Responde con recomendaciones.
 - POST `/v1/agro/ask` -> Pregunta con contexto agrícola y datos. Responde con recomendaciones.

### Parámetros del body
- question (str, requerido)
- crop (str, opcional)
- temperature (float, opcional)
- safe_mode (bool, opcional, por defecto true): fuerza redacción educativa no prescriptiva y un reintento seguro si la respuesta es bloqueada por políticas.
- length ("short" | "medium", opcional): controla la concisión de la salida. "short" produce 3-4 bullets compactos; "medium" entrega un desarrollo breve con bullets concisos.

### Ejemplo (PowerShell)
```powershell
$body = @{
  question = "Tengo maíz en V6 con hojas amarillas en bordes. ¿Qué hago?"
  crop = "maíz"
  temperature = 28
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agro/ask" -Method Post -Body $body -ContentType "application/json"
```

Ejemplo con salida más concisa (length="short"):
```powershell
$body = @{
  question = "Como ejemplo teórico, pautas generales de riego para maíz en etapa vegetativa."
  crop = "maíz"
  temperature = 25
  length = "short"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agro/ask" -Method Post -Body $body -ContentType "application/json"
```

## Notas
- En modo demo (MOCK_MODE=true o sin GEMINI_API_KEY), la API devuelve una respuesta simulada útil para flujos y pruebas.
- Para respuestas reales, coloca tu clave en `.env` y establece `MOCK_MODE=false`.
- Ajusta el modelo con `MODEL` (por defecto `gemini-1.5-pro-latest`).
 - Ajusta el modelo con `MODEL` (por defecto `gemini-1.5-pro-latest`). Recomendado: `gemini-2.5-flash` por velocidad.

## Estructura
```
app/
  main.py
  config.py
  routes/agro.py
  services/gemini_client.py
  prompts/agriculture_system_prompt.md
  schemas/
    requests.py
    responses.py
scripts/smoke_test.py
```

## Problemas comunes
- SSL/Firewall: si tienes bloqueos de red, las llamadas al modelo podrían fallar. Prueba primero en modo demo.
- Timeouts: incrementa `TIMEOUT_S` en `.env` si tu red es lenta.
- Longitud: si tu `question` es muy larga, se rechazará con 400.
