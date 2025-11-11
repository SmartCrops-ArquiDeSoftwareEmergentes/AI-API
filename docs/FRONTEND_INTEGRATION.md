Documentación Técnica del Proyecto AI-API (Backend Agrícola con Gemini)
1. Resumen del Proyecto
API en FastAPI que envuelve un modelo Gemini para producir:

Respuestas estructuradas de recomendación direccional (aumentar, disminuir, mantener) basadas en lecturas de sensores y contexto de cultivo.
Respuestas educativas en formato bullets cuando no se proporcionan parámetros cuantificables.
2. Arquitectura y Estructura de Carpetas (principal)
c:\Users\CORSAIR\Documents\GitHub\AI-API
├─ app
│  ├─ main.py
│  ├─ api
│  │  └─ v1_agro.py         (endpoint /v1/agro/ask)
│  ├─ services
│  │  └─ gemini_client.py   (llamadas al modelo + parsing JSON)
│  ├─ schemas
│  │  ├─ requests.py         (AskRequest)
│  │  └─ responses.py        (AskResponse + Recommendation)
│  ├─ prompts
│  │  └─ agriculture_system_prompt.md (prompt del sistema)
│  └─ core / utils / config (según implementación)
├─ tests
│  └─ test_ask_post.py
├─ scripts
│  └─ post_local.py
├─ requests
│  └─ ask_local.http
├─ .github
│  └─ copilot-instructions.md
├─ README.md

3. Endpoint Principal
POST /v1/agro/ask
Autenticación simple: cabecera x-api-key (validada contra variable de entorno API_KEY o valor dev en modo local).
Respuesta condicionada: si se incluye parameter + value (+ unit recomendado) => intenta generar JSON con recomendación estructurada. Caso contrario => respuesta educativa.
4. Esquema de Solicitud (Request Body JSON)
Campos útiles (opcionales salvo crop o question según uso):
{
  "question": "string (opcional si envías parámetro y valor)",
  "crop": "string",
  "temperature": 0,
  "safe_mode": true,
  "length": "short | medium",
  "parameter": "humedad_suelo | temperatura_aire | temperatura_suelo | humedad_aire | ph_suelo | ce | ndvi | lluvia | vpd | luz | nutrientes | otro",
  "value": 0,
  "unit": "%, °C, pH, dS/m, mm, lux, etc.",
  "stage": "string"
}
Descripción rápida:

question: texto libre de la consulta.
crop: cultivo (tomate, maíz, lechuga, etc.).
stage: etapa (vegetativo, floración, V6, establecimiento, etc.).
parameter: nombre del parámetro medido (ahora se recomienda usar español: humedad_suelo, temperatura_aire, temperatura_suelo, humedad_aire, ph_suelo, ce, ndvi, lluvia, vpd, luz, nutrientes, otro). También se aceptan nombres en inglés por compatibilidad; la API normaliza y siempre devuelve español.
value: valor numérico observado.
unit: unidad (%, °C, pH, etc.).
temperature: contexto adicional (opcional, si ya no es el parámetro).
safe_mode: si true, respuesta conservadora.
length: extensión deseada (short | medium | long).
5. Esquema de Respuesta (Response Body)
Caso cuantitativo (ejemplo estructurado en español):
{
  "answer": "Texto breve resumido.",
  "recommendation": {
  "action": "aumentar",
  "parameter": "humedad_suelo",
    "target_range": { "min": 22, "max": 30, "unit": "%" },
    "rationale": "Valor 18% por debajo del rango orientativo 22–30%.",
    "warnings": ["Rango estimado; ajustar según textura del suelo."]
  }
}
Caso educativo (sin parameter/value):

{
  "answer": "- Monitorea humedad del suelo...\n- Revisa signos de estrés hídrico...",
  "recommendation": null
}

6. Prompt del Sistema (Resumen)
Archivo agriculture_system_prompt.md define:

Rol: asistente agrícola de ajuste direccional (aumentar/disminuir/mantener).
Contenido permitido: rangos orientativos, acciones generales.
Prohibiciones: marcas, dosis exactas, instrucciones operativas peligrosas.
Formato JSON obligatorio cuando se incluye parámetro numérico.
Fallback: bullets educativos si no hay parámetro.
(Ver archivo para texto completo; reproducible si el frontend requiere replicar contexto.)

7. Flujo Interno de Procesamiento
Validación API key.
Construcción del mensaje al modelo con prompt del sistema + datos del usuario.
Si hay parameter/value/unit:
Se fuerza salida JSON (response_mime_type=application/json).
Se parsea el JSON; si falla, se aplica heurística local para generar recommendation segura.
Se retorna Answer + Recommendation (o sólo Answer en modo educativo).
safe_mode puede ajustar temperatura de respuesta (control de expansión textual).
8. Ejemplos Listos para /docs (Try it out)
Ejemplo A (humedad suelo baja)
{
  "question": "Lectura de humedad de suelo",
  "crop": "tomate",
  "stage": "vegetativo",
  "parameter": "humedad_suelo",
  "value": 18.0,
  "unit": "%",
  "temperature": 26,
  "safe_mode": true,
  "length": "short"
}
Ejemplo B (temperatura aire alta)
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
Ejemplo C (educativo sin parámetro)
{
  "question": "Factores para evitar estrés hídrico en maíz",
  "crop": "maíz",
  "stage": "V6",
  "safe_mode": true,
  "length": "short"
}
Ejemplo D (pH en rango)
{
  "question": "Lectura semanal de pH",
  "crop": "arándano",
  "stage": "establecimiento",
  "parameter": "ph_suelo",
  "value": 4.8,
  "unit": "pH",
  "safe_mode": true,
  "length": "short"
}
Ejemplo E (humedad aire muy alta)
{
  "question": "Humedad relativa dentro del invernadero",
  "crop": "tomate",
  "stage": "floración",
  "parameter": "humedad_aire",
Ejemplo F (luz 0 lux – sin rango genérico)
{
  "crop": "maíz",
  "parameter": "luz",
  "value": 0,
  "unit": "lux",
  "safe_mode": true,
  "length": "short"
}

Ejemplo G (lluvia 0 mm – sin rango genérico)
{
  "crop": "maíz",
  "parameter": "lluvia",
  "value": 0,
  "unit": "mm",
  "safe_mode": true,
  "length": "short"
}

Ejemplo H (nutrientes 250 – requiere contexto)
{
  "crop": "maíz",
  "parameter": "nutrientes",
  "value": 250,
  "safe_mode": true,
  "length": "short"
}
  "value": 88,
  "unit": "%",
  "safe_mode": true,
  "length": "short"
}
9. Integración Frontend (Sugerencias)
Crear formulario dinámico:
Selector cultivo (crop).
Selector etapa (stage).
Selector parámetro (parameter).
Input numérico (value) + unidad (unit).
Campo opcional pregunta (question).
Si el usuario ingresa value y parameter => mostrar bloque “Recomendación” con:
Acción (aumentar / disminuir / mantener) como etiqueta de color.
Rango objetivo (min–max unit).
Rationale en tooltip.
Warnings como lista pequeña.
Si no ingresa parámetro => mostrar bullets educativos en panel lateral.
Manejar errores:
401/403: API key incorrecta.
400: falta de datos mínimos (ni question ni parameter+value).
422: Validaciones de esquema (por ejemplo, tipos no numéricos donde corresponde).
500: Fallback genérico (“Reintentar” + log interno).
Cache ligera: almacenar última recomendación por (crop, stage, parameter) para mostrar historial.
10. Variables de Entorno
API_KEY: clave para x-api-key.
GEMINI_API_KEY / GOOGLE_API_KEY (según cliente Gemini).
ENV=dev|prod para activar logs verbose o modo demo si existe.
11. Seguridad y Bloqueos del Modelo
Prompt reduce falsos positivos evitando contenido operacional detallado.
Recomendaciones siempre genéricas y direccionales.
Warnings incluyen supuestos (evita interpretaciones peligrosas).
safe_mode habilita sesgo conservador.
12. Tests Básicos
test_ask_post.py: valida respuesta 200 y estructura recommendation si procede.
Pendientes: tests de parsing fallido JSON, tests de heurística fallback, tests de casos sin parameter.
13. Posibles Extensiones
Archivo YAML/JSON con rangos por cultivo/etapa para mayor precisión.
Endpoint /v1/agro/ranges para exponer rangos al frontend.
Historial de consultas (persistencia con SQLite/PostgreSQL).
Rate limiting por API key.
14. Items Pendientes Según Instrucciones (.github/copilot-instructions.md)
Customize the Project: agregar rangos externos configurables.
Compile the Project: asegurar instalación dependencias en README.
Create and Run Task: tasks.json para iniciar uvicorn.
Launch the Project: definir modo debug.
Ensure Documentation is Complete: incorporar esta sección al README.
15. Actualización Sugerida README
# AI-API (AgroReg)

API FastAPI que envuelve Gemini para recomendaciones agrícolas direccionales (increase, decrease, maintain) y respuestas educativas.

## Endpoints
- GET /health
- POST /v1/agro/ask

## Autenticación
Enviar cabecera:
x-api-key: TU_API_KEY

## Solicitud (POST /v1/agro/ask)
```json
{
  "question": "Lectura de humedad de suelo",
  "crop": "tomate",
  "stage": "vegetativo",
  "parameter": "soil_moisture",
  "value": 18.0,
  "unit": "%",
  "safe_mode": true,
  "length": "short"
}
```

## Respuesta (ejemplo estructurado)
```json
{
  "answer": "La humedad está por debajo del rango orientativo.",
  "recommendation": {
    "action": "increase",
    "parameter": "soil_moisture",
    "target_range": { "min": 22, "max": 30, "unit": "%" },
    "rationale": "Valor 18% menor al rango estimado 22–30%.",
    "warnings": ["Rango genérico; ajustar según textura del suelo."]
  }
}
```

## Respuesta educativa (sin parámetro)
```json
{
  "answer": "- Monitorea humedad del suelo...\n- Observa signos de estrés hídrico...",
  "recommendation": null
}
```

## Ejecución local
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Tests
```bash
.\.venv\Scripts\python.exe -m pytest -q
```

## Prompt del Sistema
Ver: app/prompts/agriculture_system_prompt.md

## Futuras mejoras
- Rangos por cultivo externos
- Historial y caching
- Endpoint de rangos

16. Errores Comunes y Soluciones
401 sin API key: agregar cabecera x-api-key.
Respuesta sin recommendation: faltan parameter/value o no se reconoce el parámetro; en casos sin rango (luz, lluvia, nutrientes) se devuelve igualmente una recomendación con min/max nulos y advertencias.
Modelo retorna texto no JSON: fallback interno; revisar logs para parse.
Unicode en guiones (–): normal; frontend puede normalizar.
17. Recomendación para Frontend AI
Proveerle:

Este README + prompt del sistema.
Esquemas de request/response.
Lista de parámetros soportados.
Comportamiento condicional (estructurado vs educativo).
Estrategia de visualización (tarjeta de recomendación + panel de bullets).
Si necesitas exportar esto en un solo archivo JSON o Markdown consolidado para consumo de otra IA, pídelo. ¿Requieres también tasks.json o archivo con rangos base? Indica.