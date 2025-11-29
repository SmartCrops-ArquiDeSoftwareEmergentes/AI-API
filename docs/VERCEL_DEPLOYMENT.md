# 🚀 Guía de Despliegue en Vercel

## ⚠️ Importante: Historial de Conversaciones

El sistema de historial con SQLite **NO funciona en Vercel** (entorno serverless). Por defecto, el historial está **deshabilitado en producción**.

### ¿Por qué SQLite no funciona en Vercel?
- ❌ Sistema de archivos efímero (se pierde entre invocaciones)
- ❌ Cada petición puede ejecutarse en un contenedor diferente
- ❌ No hay persistencia entre requests

### Solución Implementada
Se agregó la variable `ENABLE_HISTORY` que **deshabilita automáticamente** el historial en Vercel.

---

## 📋 Variables de Entorno Requeridas

### Variables Básicas (Mínimas)

```bash
# API Key de Google Gemini (REQUERIDA para modo real)
GEMINI_API_KEY=tu_clave_aqui

# Modo demo (false para usar Gemini real)
MOCK_MODE=false

# Deshabilitar historial en Vercel (IMPORTANTE)
ENABLE_HISTORY=false
```

### Variables Opcionales (Configuración Avanzada)

```bash
# Modelo de Gemini a usar
MODEL=gemini-2.5-flash

# Timeout en segundos
TIMEOUT_S=30

# Máximo de caracteres en input
MAX_INPUT_CHARS=12000

# Nivel de logging
LOG_LEVEL=INFO
```

---

## 🔧 Configuración Paso a Paso

### Opción 1: Dashboard de Vercel (Recomendado)

1. **Ve a tu proyecto en Vercel Dashboard**
   - https://vercel.com/tu-usuario/tu-proyecto

2. **Settings → Environment Variables**

3. **Agrega las siguientes variables:**

   | Variable | Value | Environment |
   |----------|-------|-------------|
   | `GEMINI_API_KEY` | `AIza...` (tu clave real) | Production |
   | `MOCK_MODE` | `false` | Production |
   | `ENABLE_HISTORY` | `false` | Production |
   | `MODEL` | `gemini-2.5-flash` | Production |

4. **Redeploy**
   - Settings → Deployments → Redeploy

### Opción 2: CLI de Vercel

```powershell
# Login (si no lo has hecho)
vercel login

# Agregar variables de entorno
vercel env add GEMINI_API_KEY production
# Pega tu clave y presiona Enter

vercel env add MOCK_MODE production
# Escribe: false

vercel env add ENABLE_HISTORY production
# Escribe: false

vercel env add MODEL production
# Escribe: gemini-2.5-flash

# Redeploy
vercel --prod
```

---

## ✅ Verificación

### 1. Verificar Health Endpoint

```powershell
# Reemplaza con tu URL de Vercel
curl https://tu-proyecto.vercel.app/health
```

**Respuesta esperada:**
```json
{
  "status": "ok",
  "mock_mode": false,
  "model": "gemini-2.5-flash",
  "history_enabled": false
}
```

✅ `mock_mode: false` → Usando Gemini real
✅ `history_enabled: false` → Historial deshabilitado (correcto para Vercel)

### 2. Probar Endpoint de Chat

```powershell
$body = @{
  question = "¿Cómo regar el tomate?"
  crop = "tomate"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://tu-proyecto.vercel.app/v1/agro/chat" `
  -Method Post `
  -Body $body `
  -ContentType "application/json"
```

**NO** debe incluir `[MODO DEMO]` en la respuesta si está configurado correctamente.

### 3. Probar Endpoint con Sensor

```powershell
$body = @{
  parameter = "humedad_suelo"
  value = 35.5
  unit = "%"
  crop = "tomate"
  stage = "floración"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://tu-proyecto.vercel.app/v1/agro/ask" `
  -Method Post `
  -Body $body `
  -ContentType "application/json"
```

Debe devolver recomendación estructurada con `action`, `target_range`, etc.

---

## 🔍 Troubleshooting

### Problema: Respuestas dicen "[MODO DEMO]"

**Causa:** `MOCK_MODE=true` o `GEMINI_API_KEY` no configurada

**Solución:**
```bash
# En Vercel Dashboard → Settings → Environment Variables
GEMINI_API_KEY = tu_clave_real
MOCK_MODE = false

# Redeploy
```

### Problema: Error 500 al acceder a /history

**Causa:** Intentando acceder a endpoints de historial con `ENABLE_HISTORY=false`

**Respuesta esperada:**
```json
{
  "detail": "Historial deshabilitado en este entorno"
}
```

Esto es **normal** en Vercel. Los endpoints de historial solo funcionan en local.

### Problema: Timeout errors

**Causa:** Gemini tarda más de 10s (límite de Vercel Hobby)

**Solución:**
```bash
# Usar modelo más rápido
MODEL = gemini-2.5-flash

# O reducir timeout interno
TIMEOUT_S = 8
```

### Problema: "Module not found: sqlalchemy"

**Causa:** `requirements.txt` no está siendo leído correctamente

**Solución:**
1. Verificar que `requirements.txt` está en la raíz del proyecto
2. Asegurar que contiene `sqlalchemy>=2.0.0`
3. Redeploy completo (no quick redeploy)

---

## 🏠 Desarrollo Local vs ☁️ Vercel

### Configuración para Local (con historial)

**`.env` local:**
```bash
GEMINI_API_KEY=tu_clave
MOCK_MODE=false
ENABLE_HISTORY=true  # ✅ Habilitado en local
MODEL=gemini-2.5-flash
```

Endpoints disponibles:
- ✅ `/v1/agro/chat`
- ✅ `/v1/agro/ask`
- ✅ `/v1/agro/history` → **Funciona**
- ✅ `/v1/agro/stats` → **Funciona**
- ✅ `/v1/agro/search` → **Funciona**

### Configuración para Vercel (sin historial)

**Variables en Vercel:**
```bash
GEMINI_API_KEY=tu_clave
MOCK_MODE=false
ENABLE_HISTORY=false  # ❌ Deshabilitado en Vercel
MODEL=gemini-2.5-flash
```

Endpoints disponibles:
- ✅ `/v1/agro/chat` → **Funciona**
- ✅ `/v1/agro/ask` → **Funciona**
- ❌ `/v1/agro/history` → Error 503
- ❌ `/v1/agro/stats` → Error 503
- ❌ `/v1/agro/search` → Error 503

---

## 🎯 Resumen

### Variables Mínimas para Vercel
```bash
GEMINI_API_KEY = tu_clave_real
MOCK_MODE = false
ENABLE_HISTORY = false
```

### Verificación Rápida
```powershell
# Debe retornar history_enabled: false
curl https://tu-proyecto.vercel.app/health
```

### Comandos Completos para Deploy

```powershell
# 1. Login
vercel login

# 2. Configurar variables
vercel env add GEMINI_API_KEY production
vercel env add MOCK_MODE production
vercel env add ENABLE_HISTORY production

# 3. Deploy
vercel --prod

# 4. Verificar
curl https://tu-proyecto.vercel.app/health
```

---

## 💡 Alternativas para Historial en Producción

Si necesitas historial en producción, considera:

### Opción A: Base de Datos Externa
- **Supabase** (PostgreSQL gratis): https://supabase.com
- **PlanetScale** (MySQL gratis): https://planetscale.com
- **Neon** (PostgreSQL gratis): https://neon.tech

Cambiar en `app/db/database.py`:
```python
# En lugar de SQLite
# engine = create_engine("sqlite:///./agriculture_history.db")

# Usar PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
```

Agregar variable en Vercel:
```bash
DATABASE_URL = postgresql://usuario:password@host:5432/database
ENABLE_HISTORY = true
```

### Opción B: Redis para Caché
- **Upstash Redis** (gratis): https://upstash.com
- Almacenar solo últimas 100 conversaciones
- Suficiente para demos y monitoreo básico

### Opción C: Logging Externo
- **Logtail**: https://logtail.com
- **Better Stack**: https://betterstack.com
- Solo para análisis, no para consultas del usuario

---

## 📚 Recursos Adicionales

- [Documentación de Vercel Functions](https://vercel.com/docs/functions)
- [Límites de Vercel](https://vercel.com/docs/limits)
- [Google Gemini API](https://ai.google.dev/)

---

## ⚡ Quick Start

```powershell
# Deploy en 3 comandos
vercel login
vercel env add GEMINI_API_KEY production  # Pega tu clave
vercel env add ENABLE_HISTORY production  # Escribe: false
vercel --prod

# Verificar
curl https://tu-deploy.vercel.app/health
```

¡Listo! 🎉
