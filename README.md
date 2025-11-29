# Agro Gemini API

Una API en FastAPI que envuelve Google Gemini para entregar orientación educativa y, cuando se proporcionan lecturas de sensores, recomendaciones direccionales estructuradas (increase/decrease/maintain) con rango objetivo orientativo.

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

## Despliegue en Vercel
Este proyecto está listo para ser desplegado como Función Serverless de Python en Vercel.

- Estructura: el entrypoint para Vercel es `api/index.py`, que expone la app ASGI.
- Configuración de rutas: `vercel.json` redirige todo a `api/index.py`.
- Requisitos en Vercel: Vercel instala automáticamente las dependencias detectando `requirements.txt`.

### ⚠️ Importante: Historial en Vercel
El sistema de historial SQLite **NO funciona en Vercel** (serverless). Se debe deshabilitar con la variable `ENABLE_HISTORY=false`.

### Variables de entorno REQUERIDAS en Vercel:
```bash
GEMINI_API_KEY = tu_clave_real       # Obligatoria
MOCK_MODE = false                     # Para usar Gemini real
ENABLE_HISTORY = false                # IMPORTANTE: Deshabilitar historial
```

### Variables opcionales:
- `MODEL` (opcional): por defecto `gemini-1.5-pro-latest` (recomendado: `gemini-2.5-flash`).
- `LOG_LEVEL` (opcional): `INFO` por defecto.
- `TIMEOUT_S` (opcional): `30` por defecto.
- `MAX_INPUT_CHARS` (opcional): `12000` por defecto.

### Pasos de despliegue:

**Opción 1: CLI (Rápido)**
```cmd
vercel login
vercel env add GEMINI_API_KEY production    # Pega tu clave
vercel env add MOCK_MODE production         # Escribe: false
vercel env add ENABLE_HISTORY production    # Escribe: false
vercel --prod
```

**Opción 2: Dashboard de Vercel**
1. Ve a Settings → Environment Variables
2. Agrega las 3 variables requeridas
3. Redeploy desde Deployments

📖 **Guía completa**: Ver [`docs/VERCEL_DEPLOYMENT.md`](docs/VERCEL_DEPLOYMENT.md)

3) Probar endpoints desplegados (reemplaza la URL):
```powershell
$base = "https://tu-deploy.vercel.app"
Invoke-RestMethod -Uri "$base/health" -Method Get

$body = @{ question = "Tengo maíz en V6 con hojas amarillas en bordes. ¿Qué hago?"; crop = "maíz"; temperature = 28 } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri "$base/v1/agro/ask" -Method Post -Body $body -ContentType "application/json"
```

### Salir del modo DEMO en Vercel
Si recibes respuestas con `[MODO DEMO]`, significa que el servicio está en modo simulado. Para respuestas reales, configura:

- Define `GEMINI_API_KEY` en el entorno (Producción) de Vercel.
- Establece `MOCK_MODE=false` en el entorno (Producción).
- Redeploya el proyecto para aplicar los cambios.

CLI (interactivo) en Windows:
```cmd
vercel env add GEMINI_API_KEY production
# Pega tu clave y confirma
vercel env add MOCK_MODE production
# Escribe: false

# Después de actualizar variables, redeploya
vercel --prod
```

Verificación rápida:
- `GET /health` debe devolver `"mock_mode": false` y el nombre de modelo.
- `POST /v1/agro/ask` ya no incluirá la etiqueta `[MODO DEMO]`.

Notas para serverless:
- El archivo de prompt está embebido con un fallback si no se puede leer desde disco (útil en entornos serverless).
- Si no defines `GEMINI_API_KEY` o hay error al configurar el cliente, la API cae automáticamente en modo demo.

## Endpoints
- GET `/health` → Estado del servicio, modelo y modo demo
- POST `/v1/agro/chat` → **Consulta de texto libre** (chatbot/textbox simple)
- POST `/v1/agro/ask` → Recomendaciones con sensores o respuesta educativa
- GET `/v1/agro/history` → **Historial de conversaciones** (nuevo!)
- GET `/v1/agro/history/{chat_id}` → Detalle de una conversación específica
- GET `/v1/agro/sensors/history` → Historial de lecturas de sensores
- GET `/v1/agro/stats` → Estadísticas de uso
- GET `/v1/agro/search` → Búsqueda en historial

Ver documentación completa de historial en [`docs/HISTORY_API.md`](docs/HISTORY_API.md).

### Diferencias entre endpoints
**`/v1/agro/chat`**: Para preguntas generales en texto libre sin datos de sensores.
- Entrada: solo `question` (+ opcionales `crop`, `stage`, `length`)
- Salida: `answer` educativo en texto/bullets

**`/v1/agro/ask`**: Para tableros con datos de sensores o consultas mixtas.
- Entrada: `question` O (`parameter` + `value`)
- Salida: recomendación estructurada (aumentar/disminuir/mantener) cuando hay sensores, o texto educativo si no

### Parámetros del body
- question (str, requerido)
- crop (str, opcional)
- temperature (float, opcional)
- safe_mode (bool, opcional, por defecto true)
- length ("short" | "medium", opcional)
- parameter (str, opcional): nombre del parámetro medido (usar español preferentemente: humedad_suelo, temperatura_aire, temperatura_suelo, humedad_aire, ph_suelo, ce, ndvi, lluvia, vpd, otro)
- value (float, opcional): valor observado del parámetro
- unit (str, opcional): unidad del parámetro (%, °C, pH, dS/m, mm, etc.)
- stage (str, opcional): etapa fenológica (ej. V6, floración)

Si se incluyen `parameter` y `value`, la API intenta devolver un objeto estructurado `recommendation` además del campo `answer` textual.

### Ejemplo (PowerShell)

**Chat simple (texto libre):**
```powershell
$body = @{
  question = "¿Qué factores afectan el crecimiento de lechuga en hidroponía?"
  crop = "lechuga"
  length = "short"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agro/chat" -Method Post -Body $body -ContentType "application/json"
```

**Ask con sensores (recomendación estructurada):**
```powershell
$body = @{
  question = "Tengo maíz en V6 con hojas amarillas en bordes. ¿Qué hago?"
  crop = "maíz"
  temperature = 28
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agro/ask" -Method Post -Body $body -ContentType "application/json"
```

Ejemplo con recomendación estructurada (sensor):
```powershell
$body = @{
  question = "Lectura de humedad de suelo para maíz V6"
  crop = "maíz"
  stage = "V6"
  parameter = "soil_moisture"
  value = 18.5
  unit = "%"
  temperature = 26
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agro/ask" -Method Post -Body $body -ContentType "application/json"
```
Respuesta esperada (ejemplo en español):
```json
{
  "answer": "Sugerencia: aumentar humedad_suelo. Rango objetivo: 20–30 %. Valor observado por debajo del intervalo típico para maíz en fase vegetativa temprana.",
  "model": "gemini-2.5-flash",
  "recommendation": {
  "action": "aumentar",
  "parameter": "humedad_suelo",
    "target_range": {"min": 20.0, "max": 30.0, "unit": "%"},
    "rationale": "El valor 18.5% está ligeramente por debajo del rango general orientativo (20–30%) para soporte óptimo de crecimiento vegetativo.",
    "warnings": ["Rango genérico: ajustar según textura y capacidad de campo específica."]
  }
}
```

Nota: Los rangos son orientativos y pueden variar por suelo, clima y manejo local; la salida evita dosis o instrucciones operativas específicas.
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
api/
  index.py
vercel.json
scripts/smoke_test.py
```

## Problemas comunes
- SSL/Firewall: si tienes bloqueos de red, las llamadas al modelo podrían fallar. Prueba primero en modo demo.
- Timeouts: incrementa `TIMEOUT_S` en `.env` si tu red es lenta.
- Longitud: si tu `question` es muy larga, se rechazará con 400.
