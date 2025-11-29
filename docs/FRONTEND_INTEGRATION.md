Documentación Técnica de Integración Frontend (AI-API)

1. Resumen
La API en FastAPI envuelve Gemini para producir dos tipos de salida (siempre en español):
* Recomendación direccional estructurada (aumentar | disminuir | mantener) cuando se envían lecturas cuantificables (parameter + value).
* Resumen educativo en bullets cuando NO se envía parámetro medible.

2. Arquitectura Real del Repo
```
app/
  main.py
  routes/agro.py              # /health y /v1/agro/ask
  services/gemini_client.py   # llamada al modelo + fallback heurístico
  schemas/requests.py         # AskRequest
  schemas/responses.py        # AskResponse, Recommendation, TargetRange
  prompts/agriculture_system_prompt.md
  utils/logger.py, sanitize.py
api/index.py                  # entrypoint Vercel
vercel.json
scripts/smoke_test.py         # prueba rápida local
README.md
docs/FRONTEND_INTEGRATION.md  # este archivo
requirements.txt
```
No existe `app/api/v1_agro.py`, carpeta `tests/` ni `requests/` actualmente. (Agregar en el futuro si se crean pruebas formales.)

3. Endpoints
* GET `/health` -> estado, mock_mode, modelo.
* POST `/v1/agro/chat` -> **NUEVO**: Consulta de texto libre (solo pregunta, sin sensores). Responde con texto educativo.
* POST `/v1/agro/ask` -> Recomendación direccional (con sensores) o resumen educativo (sin sensores).

**Diferencia entre /chat y /ask:**
* `/chat`: Textbox simple para preguntas generales → devuelve solo `answer`, `model`, `tips`.
* `/ask`: Formulario completo con sensores → devuelve `answer` + `recommendation` estructurada cuando hay datos de sensores.

Autenticación: hoy NO se valida ninguna API key en el código. Si el frontend necesita auth, deberá añadirse lógica (cabecera `x-api-key`) en `routes/agro.py`. Hasta entonces, omitir la cabecera.

4. Esquemas de Solicitud

### 4.1 ChatRequest (para /v1/agro/chat)
```
{
  "question": "string (requerido)",
  "crop": "string?",
  "stage": "string?",
  "length": "short" | "medium"? (default: medium),
  "safe_mode": boolean? (default: true)
}
```
Respuesta ChatResponse:
```
{
  "answer": "string",
  "model": "string",
  "tips": ["string", ...] | null
}
```

### 4.2 AskRequest (para /v1/agro/ask)
Campos (todos opcionales salvo que se requiere al menos `question` O (`parameter` + `value`)):
```
{
  "question": "string?",
  "crop": "string?",
  "temperature": number?,
  "safe_mode": boolean? (default true),
  "length": "short" | "medium"?,
  "parameter": "humedad_suelo | temperatura_aire | temperatura_suelo | humedad_aire | ph_suelo | ce | ndvi | lluvia | vpd | luz | nutrientes | otro"?,
  "value": number?,
  "unit": "string?",
  "stage": "string?"
}
```
Notas:
* `length` sólo admite `short` o `medium` (el prompt interno ajusta tokens). No existe `long`.
* Se aceptan parámetros en inglés equivalentes: soil_moisture, air_temperature, etc. Internamente se normalizan y al responder se devuelven en español.
* Si se envía `parameter` sin `value` se obtendrá error 400.
* `safe_mode=true` mantiene tono muy educativo y activa reframings si el modelo bloquea.

5. Traducción de Parámetros (interno -> salida)
```
soil_moisture -> humedad_suelo
air_temperature -> temperatura_aire
soil_temperature -> temperatura_suelo
air_humidity -> humedad_aire
soil_ph -> ph_suelo
ec -> ce
ndvi -> ndvi
rain -> lluvia
light -> luz
nutrients -> nutrientes
vpd -> vpd
other -> otro
```

6. Esquema de Respuesta (AskResponse)
```
{
  "answer": "string",
  "model": "string",
  "usage": { ... } | null,
  "tips": ["string", ...] | null,
  "recommendation": {
    "action": "aumentar | disminuir | mantener",
    "parameter": "<parametro_en_español>",
    "target_range": {"min": number|null, "max": number|null, "unit": "string|null"},
    "rationale": "string",
    "warnings": ["string", ...]
  } | null
}
```
Si el modelo falla al generar JSON estructurado se usa una heurística interna para producir la recomendación (con rangos genéricos o nulos).

7. Rangos y Casos Especiales
* Parámetros con rangos genéricos: humedad_suelo (20–30 %), temperatura_aire (18–30 °C), temperatura_suelo (15–25 °C), humedad_aire (50–80 %), ph_suelo (6.0–7.5), ce (0.8–2.5 dS/m), ndvi (0.5–0.9), vpd (0.8–1.5 kPa).
* Parámetros SIN rango confiable universal: luz, lluvia, nutrientes -> se devuelven `min=null`, `max=null` y advertencias explicativas; acción por defecto suele ser `mantener` salvo que futura lógica indique otra dirección.

8. Ejemplos para Swagger (/docs)

### Ejemplos para /v1/agro/chat (texto libre)
**Chat 1: Pregunta general**
```
{
  "question": "¿Qué factores afectan el crecimiento de lechuga en hidroponía?",
  "crop": "lechuga",
  "length": "short"
}
```
**Chat 2: Consulta sobre manejo**
```
{
  "question": "Estrategias para mejorar la retención de agua en suelos arenosos",
  "length": "medium"
}
```

### Ejemplos para /v1/agro/ask (sensores)
**Ejemplo A (humedad suelo baja)**
```
{
  "question": "Lectura de humedad de suelo",
  "crop": "tomate",
  "stage": "vegetativo",
  "parameter": "humedad_suelo",
  "value": 18.0,
  "unit": "%",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo B (temperatura aire alta)
```
{
  "question": "Temperatura del invernadero",
  "crop": "lechuga",
  "stage": "desarrollo",
  "parameter": "temperatura_aire",
  "value": 29.5,
  "unit": "°C",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo C (educativo sin parámetro)
```
{
  "question": "Factores para evitar estrés hídrico en maíz",
  "crop": "maíz",
  "stage": "V6",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo D (pH en rango)
```
{
  "question": "Lectura semanal de pH",
  "crop": "arándano",
  "stage": "establecimiento",
  "parameter": "ph_suelo",
  "value": 6.2,
  "unit": "pH",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo E (humedad aire muy alta)
```
{
  "question": "Humedad relativa dentro del invernadero",
  "crop": "tomate",
  "stage": "floración",
  "parameter": "humedad_aire",
  "value": 88,
  "unit": "%",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo F (luz sin rango genérico)
```
{
  "crop": "maíz",
  "parameter": "luz",
  "value": 0,
  "unit": "lux",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo G (lluvia sin rango genérico)
```
{
  "crop": "maíz",
  "parameter": "lluvia",
  "value": 0,
  "unit": "mm",
  "safe_mode": true,
  "length": "short"
}
```
Ejemplo H (nutrientes requiere contexto)
```
{
  "crop": "maíz",
  "parameter": "nutrientes",
  "value": 250,
  "safe_mode": true,
  "length": "short"
}
```

9. Integración Frontend (UI/UX)

### Opción 1: Textbox Simple (/v1/agro/chat)
Para casos de uso tipo chatbot o consulta rápida:
* Un `<textarea>` para la pregunta.
* Selects opcionales para cultivo y etapa.
* Botón "Preguntar".
* Renderiza la respuesta `answer` en un panel de texto o markdown.

### Opción 2: Formulario Completo (/v1/agro/ask)
Para tableros de sensores o monitoreo:
* Select cultivo (`crop`).
* Select etapa (`stage`).
* Select parámetro (`parameter`).
* Input numérico (`value`) + select unidad (`unit`).
* Campo de texto (`question`) opcional.

Renderizado:
* Si existe `recommendation` -> tarjeta con:
  - Acción (badge con colores: aumentar=verde, disminuir=rojo, mantener=azul/gris).
  - Parámetro y rango (si disponible) `min–max unit`.
  - Rationale (tooltip o bloque secundario).
  - Warnings (lista compacta).
* Si no hay `recommendation` -> panel de bullets educativos (puede parsearse por saltos de línea).

10. Manejo de Errores HTTP
* 400: faltan datos mínimos (ni question ni parameter+value) o pregunta demasiado larga.
* 502: error al contactar el modelo (mostrar mensaje “Servicio temporalmente indisponible, reintenta”).
* 422: error de validación de tipos (Pydantic) – mostrar detalle.
* Otros: fallback genérico y log interno.

11. Estado Demo vs Real
Si `settings.mock_mode` fuese true (no llave de Gemini), la respuesta incluiría tag `[MODO DEMO]` (hoy no se está en demo). El frontend puede detectar substring y mostrar banner “Resultados simulados”.

12. Heurística vs Modelo
* Flujo preferente: modelo genera JSON.
* Si falla: heurística produce recomendación direccional usando rangos genéricos.
* En parámetros sin rango -> acción `mantener` + advertencias para solicitar mayor contexto.

13. Ejemplo de Consumo en JavaScript (fetch)

### Chat (texto libre)
```js
async function preguntarChat(question, crop = null, length = 'medium') {
  const res = await fetch('http://127.0.0.1:8000/v1/agro/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, crop, length })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`Error ${res.status}: ${err.detail || 'fallo desconocido'}`);
  }
  return res.json();
}

// Uso
preguntarChat('¿Cómo riego tomates en verano?', 'tomate', 'short')
  .then(data => console.log(data.answer))
  .catch(console.error);
```

### Ask (sensores)
```js
async function pedirRecomendacion(payload) {
  const res = await fetch('http://127.0.0.1:8000/v1/agro/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`Error ${res.status}: ${err.detail || 'fallo desconocido'}`);
  }
  return res.json();
}

// Ejemplo de uso
pedirRecomendacion({
  question: 'Lectura de humedad de suelo',
  crop: 'tomate',
  parameter: 'humedad_suelo',
  value: 18.0,
  unit: '%',
  length: 'short'
}).then(console.log).catch(console.error);
```

14. Tipos TypeScript (sugeridos)

### Chat
```ts
export interface ChatRequest {
  question: string;
  crop?: string;
  stage?: string;
  length?: 'short' | 'medium';
  safe_mode?: boolean;
}
export interface ChatResponse {
  answer: string;
  model: string;
  tips?: string[] | null;
}
```

### Ask (sensores)
```ts
export interface TargetRange { min: number | null; max: number | null; unit: string | null; }
export interface Recommendation {
  action: 'aumentar' | 'disminuir' | 'mantener';
  parameter: string;
  target_range: TargetRange | null;
  rationale: string | null;
  warnings: string[] | null;
}
export interface AskResponse {
  answer: string;
  model: string;
  usage?: Record<string, any> | null;
  tips?: string[] | null;
  recommendation?: Recommendation | null;
}
```

15. Consideraciones de Encoding
Usar UTF-8. Algunos guiones en-dash “–” pueden aparecer; normalizar a “-” si afecta el layout. Verificar correcto render de tildes y caracteres especiales.

16. Guardrails Futuras (no implementadas aún)
* pH fuera de [0,14] -> advertencia / rechazo.
* humedad_suelo > 100% -> advertencia.
* valores negativos en parámetros no negativos -> rechazo 400.
* unidad incompatible (p.ej. °C para ph_suelo) -> advertencia automática.

17. Extensiones Planeadas
* Archivo externo con rangos por cultivo + etapa.
* Endpoint `/v1/agro/ranges`.
* Historial y cache per usuario.
* Autenticación por API key y rate limiting.

18. Checklist Diferencias con README
* Este documento ya refleja la ausencia de auth actual.
* Limita `length` a short/medium.
* Añade ejemplos corregidos y no truncados.
* Proporciona tipos y snippet fetch.

19. Frontend AI (otro modelo)
Si otro modelo (ej. para UI) necesita contexto, proveer: archivo de prompt, lista de parámetros soportados, este doc y ejemplos A–H. Pedir siempre acción, rango, rationale y warnings para consistencia visual.

20. Export Consolidado
Si se requiere un único JSON con esquemas + ejemplos para bootstrap del frontend, solicitarlo y se generará.

Fin del documento.