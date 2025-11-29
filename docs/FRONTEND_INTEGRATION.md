# Documentación de Integración Frontend (AI-API)

## 📋 Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura](#2-arquitectura)
3. [Endpoints Disponibles](#3-endpoints-disponibles)
4. [🚀 Quick Start: Chat Simple (Recomendado para Empezar)](#4-quick-start-chat-simple)
5. [🔬 Implementación Avanzada: Ask con Sensores](#5-implementación-avanzada-ask-con-sensores)
6. [📊 Historial de Conversaciones (Opcional)](#6-historial-de-conversaciones-opcional)
7. [Esquemas Completos](#7-esquemas-completos)
8. [Ejemplos de Uso](#8-ejemplos-de-uso)
9. [Tipos TypeScript](#9-tipos-typescript)
10. [Manejo de Errores](#10-manejo-de-errores)

---

## 1. Resumen Ejecutivo

La API ofrece **dos modos de uso**:

### ✅ Chat Simple (Funciona SIEMPRE: Local + Vercel)
- Endpoint: `POST /v1/agro/chat`
- Uso: Textbox simple → pregunta en lenguaje natural
- Ideal para: Chatbots, FAQ, consultas generales
- **Sin dependencias**: Funciona sin historial, sin sensores

### ⚡ Ask Avanzado (Funciona SIEMPRE: Local + Vercel)
- Endpoint: `POST /v1/agro/ask`
- Uso: Sensores + recomendaciones estructuradas
- Ideal para: Dashboards IoT, monitoreo en tiempo real
- **Sin dependencias**: Funciona sin historial

### 📊 Historial (SOLO Local)
- Endpoints: `/v1/agro/history`, `/stats`, `/search`
- Uso: Ver conversaciones pasadas, estadísticas
- **Solo disponible en desarrollo local**
- En Vercel retorna error 503 (normal)

---

## 2. Arquitectura

```
app/
  main.py
  routes/agro.py              # Todos los endpoints
  services/gemini_client.py   # Lógica de Gemini
  schemas/
    requests.py               # AskRequest
    responses.py              # AskResponse
    chat.py                   # ChatRequest, ChatResponse
  prompts/agriculture_system_prompt.md
  db/
    database.py               # SQLite (solo local)
    history_service.py        # CRUD historial
api/index.py                  # Entrypoint Vercel
vercel.json                   # Config serverless
```

---

## 3. Endpoints Disponibles

### Endpoints Principales (Funcionan en Local + Vercel)

| Endpoint | Método | Descripción | Disponible en Vercel |
|----------|--------|-------------|---------------------|
| `/health` | GET | Estado del servicio | ✅ Sí |
| `/v1/agro/chat` | POST | Chat de texto libre | ✅ Sí |
| `/v1/agro/ask` | POST | Sensores + recomendaciones | ✅ Sí |

### Endpoints de Historial (Solo Local)

| Endpoint | Método | Descripción | Disponible en Vercel |
|----------|--------|-------------|---------------------|
| `/v1/agro/history` | GET | Lista conversaciones | ❌ No (error 503) |
| `/v1/agro/history/{id}` | GET | Detalle de conversación | ❌ No (error 503) |
| `/v1/agro/sensors/history` | GET | Historial de sensores | ❌ No (error 503) |
| `/v1/agro/stats` | GET | Estadísticas de uso | ❌ No (error 503) |
| `/v1/agro/search` | GET | Búsqueda en historial | ❌ No (error 503) |

---

## 4. 🚀 Quick Start: Chat Simple

### 4.1 ¿Cuándo usar Chat?

✅ **Usa `/v1/agro/chat` cuando:**
- Tienes un textbox simple (tipo ChatGPT)
- Usuario pregunta en lenguaje natural
- NO tienes datos de sensores
- Quieres respuestas educativas/informativas

### 4.2 Request Schema

```typescript
interface ChatRequest {
  question: string;          // REQUERIDO: Pregunta del usuario
  crop?: string;             // Opcional: "tomate", "maíz", etc.
  stage?: string;            // Opcional: "floración", "vegetativo"
  length?: 'short' | 'medium'; // Opcional: default 'medium'
  safe_mode?: boolean;       // Opcional: default true
}
```

### 4.3 Response Schema

```typescript
interface ChatResponse {
  answer: string;    // Respuesta en texto/bullets
  model: string;     // Modelo usado (ej: "gemini-2.5-flash")
  tips?: string[];   // Tips adicionales (opcional)
}
```

### 4.4 Ejemplo JavaScript/React

```jsx
// Componente React simple
function ChatBot() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          crop: 'tomate',
          length: 'short'
        })
      });

      if (!res.ok) throw new Error(`Error ${res.status}`);
      
      const data = await res.json();
      setAnswer(data.answer);
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="¿Cómo regar el tomate?"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Pensando...' : 'Preguntar'}
        </button>
      </form>
      {answer && <div className="answer">{answer}</div>}
    </div>
  );
}
```

### 4.5 Ejemplos de Preguntas

```javascript
// Pregunta general
{
  "question": "¿Qué factores afectan el crecimiento de lechuga en hidroponía?",
  "crop": "lechuga",
  "length": "short"
}

// Consulta sobre manejo
{
  "question": "Estrategias para mejorar la retención de agua en suelos arenosos"
}

// Pregunta específica de cultivo
{
  "question": "¿Cuándo cosechar tomates?",
  "crop": "tomate",
  "stage": "fructificación"
}
```

### 4.6 Renderizado de Respuestas

La respuesta viene en formato texto con bullets (`•`). Puedes renderizarla directamente:

```jsx
function AnswerDisplay({ answer }) {
  // Convertir bullets en lista HTML
  const lines = answer.split('\n');
  
  return (
    <div className="answer">
      {lines.map((line, i) => {
        if (line.trim().startsWith('•')) {
          return <li key={i}>{line.replace('•', '').trim()}</li>;
        }
        return <p key={i}>{line}</p>;
      })}
    </div>
  );
}
```

---

## 5. 🔬 Implementación Avanzada: Ask con Sensores

### 5.1 ¿Cuándo usar Ask?

✅ **Usa `/v1/agro/ask` cuando:**
- Tienes datos de sensores IoT
- Necesitas recomendaciones estructuradas (aumentar/disminuir/mantener)
- Quieres rangos objetivo específicos
- Estás construyendo un dashboard de monitoreo

### 5.2 Request Schema

```typescript
interface AskRequest {
  // Opción 1: Solo pregunta (modo educativo)
  question?: string;
  
  // Opción 2: Datos de sensor (modo recomendación)
  parameter?: string;  // "humedad_suelo", "temperatura_aire", etc.
  value?: number;      // Valor medido
  unit?: string;       // "%", "°C", "pH", etc.
  
  // Contexto (opcional)
  crop?: string;       // "tomate", "maíz", etc.
  stage?: string;      // "floración", "vegetativo", etc.
  
  // Configuración
  length?: 'short' | 'medium';
  safe_mode?: boolean;
}
```

**Regla**: Debes enviar `question` **O** (`parameter` + `value`).

### 5.3 Response Schema

```typescript
interface AskResponse {
  answer: string;    // Explicación en texto
  model: string;     // Modelo usado
  tips?: string[];   // Tips adicionales
  
  // Solo cuando hay datos de sensor:
  recommendation?: {
    action: 'aumentar' | 'disminuir' | 'mantener';
    parameter: string;  // En español: "humedad_suelo"
    target_range: {
      min: number | null;
      max: number | null;
      unit: string | null;
    } | null;
    rationale: string;
    warnings: string[];
  };
}
```

### 5.4 Parámetros Soportados

```typescript
type Parameter = 
  | 'humedad_suelo'       // Soil moisture
  | 'temperatura_aire'    // Air temperature
  | 'temperatura_suelo'   // Soil temperature
  | 'humedad_aire'        // Air humidity
  | 'ph_suelo'            // Soil pH
  | 'ce'                  // Electrical conductivity
  | 'ndvi'                // Vegetation index
  | 'vpd'                 // Vapor pressure deficit
  | 'lluvia'              // Rainfall (sin rango genérico)
  | 'luz'                 // Light (sin rango genérico)
  | 'nutrientes'          // Nutrients (sin rango genérico)
  | 'otro';               // Other
```

**Nota**: También aceptamos equivalentes en inglés (`soil_moisture`, `air_temperature`, etc.) que se normalizan automáticamente.

### 5.5 Ejemplo React Dashboard

```jsx
function SensorDashboard() {
  const [sensorData, setSensorData] = useState({
    parameter: 'humedad_suelo',
    value: 35.5,
    unit: '%',
    crop: 'tomate',
    stage: 'floración'
  });
  const [recommendation, setRecommendation] = useState(null);

  const getRecommendation = async () => {
    const res = await fetch('https://tu-api.vercel.app/v1/agro/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sensorData)
    });

    const data = await res.json();
    setRecommendation(data.recommendation);
  };

  return (
    <div className="dashboard">
      <div className="sensor-input">
        <select onChange={(e) => setSensorData({...sensorData, parameter: e.target.value})}>
          <option value="humedad_suelo">Humedad de Suelo</option>
          <option value="temperatura_aire">Temperatura del Aire</option>
          <option value="ph_suelo">pH del Suelo</option>
        </select>
        
        <input
          type="number"
          value={sensorData.value}
          onChange={(e) => setSensorData({...sensorData, value: parseFloat(e.target.value)})}
        />
        
        <button onClick={getRecommendation}>Obtener Recomendación</button>
      </div>

      {recommendation && (
        <div className={`recommendation ${recommendation.action}`}>
          <h3>Acción: {recommendation.action.toUpperCase()}</h3>
          <p>Parámetro: {recommendation.parameter}</p>
          
          {recommendation.target_range && (
            <p>
              Rango objetivo: {recommendation.target_range.min} - {recommendation.target_range.max} {recommendation.target_range.unit}
            </p>
          )}
          
          <p className="rationale">{recommendation.rationale}</p>
          
          {recommendation.warnings.length > 0 && (
            <ul className="warnings">
              {recommendation.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
```

### 5.6 CSS Sugerido para Recomendaciones

```css
.recommendation {
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.recommendation.aumentar {
  background: #d4edda;
  border-left: 4px solid #28a745;
}

.recommendation.disminuir {
  background: #f8d7da;
  border-left: 4px solid #dc3545;
}

.recommendation.mantener {
  background: #d1ecf1;
  border-left: 4px solid #17a2b8;
}

.warnings {
  margin-top: 0.5rem;
  color: #856404;
  background: #fff3cd;
  padding: 0.5rem;
  border-radius: 4px;
}
```

---

## 6. 📊 Historial de Conversaciones (Opcional)

### 6.1 ¿Cuándo está disponible?

- ✅ **Local**: Funciona perfectamente con SQLite
- ❌ **Vercel**: NO disponible (retorna error 503)

### 6.2 ¿Cómo implementar?

#### Opción A: Solo Chat (Sin Historial)

**Perfecto para Vercel** - La implementación más simple:

```jsx
// NO necesitas llamar a /history
// Solo usa /chat o /ask según necesites
function SimpleChat() {
  const [messages, setMessages] = useState([]);
  
  const sendMessage = async (question) => {
    const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    
    const data = await res.json();
    setMessages([...messages, { question, answer: data.answer }]);
  };
  
  return (/* UI simple sin historial persistente */);
}
```

**Ventajas**:
- ✅ Funciona en Vercel
- ✅ Sin base de datos
- ✅ Implementación rápida
- ✅ Mantiene historial solo en memoria (durante la sesión)

#### Opción B: Chat + Historial Local

**Solo para desarrollo local** - Permite ver conversaciones pasadas:

```jsx
function ChatWithHistory() {
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const API_URL = 'http://localhost:8000'; // Solo local

  // Cargar historial al montar
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/v1/agro/history?limit=20`);
      const data = await res.json();
      setHistory(data.chats);
    } catch (error) {
      // En Vercel retorna 503, manejar gracefully
      console.log('Historial no disponible');
    }
  };

  const sendMessage = async (question) => {
    const res = await fetch(`${API_URL}/v1/agro/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, crop: 'tomate' })
    });
    
    const data = await res.json();
    setMessages([...messages, { question, answer: data.answer }]);
    
    // Recargar historial
    loadHistory();
  };

  return (
    <div className="chat-container">
      {/* Sidebar con historial (solo local) */}
      <aside className="history-sidebar">
        <h3>Conversaciones Anteriores</h3>
        {history.map(chat => (
          <div key={chat.id} className="history-item">
            <small>{new Date(chat.timestamp).toLocaleString()}</small>
            <p>{chat.question}</p>
          </div>
        ))}
      </aside>

      {/* Chat principal */}
      <main className="chat-main">
        {messages.map((msg, i) => (
          <div key={i}>
            <div className="user-message">{msg.question}</div>
            <div className="bot-message">{msg.answer}</div>
          </div>
        ))}
        {/* Input para nueva pregunta */}
      </main>
    </div>
  );
}
```

### 6.3 Endpoints de Historial (Solo Local)

#### GET `/v1/agro/history`
Lista conversaciones recientes.

```typescript
// Request
fetch('http://localhost:8000/v1/agro/history?limit=20&crop=tomate')

// Response
{
  "total": 15,
  "chats": [
    {
      "id": 42,
      "timestamp": "2025-11-29T21:30:00",
      "endpoint": "/v1/agro/chat",
      "question": "¿Cómo regar el tomate?",
      "crop": "tomate",
      "answer_preview": "El riego del tomate requiere...",
      "model": "gemini-2.5-flash",
      "response_time_ms": 520
    }
  ]
}
```

#### GET `/v1/agro/history/{chat_id}`
Detalle completo de una conversación.

```typescript
fetch('http://localhost:8000/v1/agro/history/42')

// Response incluye answer completo + recommendation si existe
```

#### GET `/v1/agro/stats`
Estadísticas de uso.

```typescript
fetch('http://localhost:8000/v1/agro/stats')

// Response
{
  "total_conversations": 245,
  "total_sensor_readings": 156,
  "top_crops": [
    {"crop": "tomate", "count": 89},
    {"crop": "maíz", "count": 67}
  ],
  "top_parameters": [
    {"parameter": "humedad_suelo", "count": 78}
  ],
  "avg_response_time_ms": 485.32
}
```

#### GET `/v1/agro/search`
Buscar en historial.

```typescript
fetch('http://localhost:8000/v1/agro/search?q=riego&limit=10')

// Response similar a /history pero filtrado por término
```

### 6.4 Verificar si Historial está Disponible

```jsx
async function checkHistoryAvailable() {
  try {
    const res = await fetch(`${API_URL}/health`);
    const data = await res.json();
    return data.history_enabled; // true en local, false en Vercel
  } catch {
    return false;
  }
}

// Uso en componente
function App() {
  const [historyEnabled, setHistoryEnabled] = useState(false);

  useEffect(() => {
    checkHistoryAvailable().then(setHistoryEnabled);
  }, []);

  return historyEnabled ? <ChatWithHistory /> : <SimpleChat />;
}
```

---

## 7. Esquemas Completos

### 7.1 Traducción de Parámetros

```typescript
// Entrada (inglés) -> Salida (español)
const parameterMapping = {
  'soil_moisture': 'humedad_suelo',
  'air_temperature': 'temperatura_aire',
  'soil_temperature': 'temperatura_suelo',
  'air_humidity': 'humedad_aire',
  'soil_ph': 'ph_suelo',
  'ec': 'ce',
  'ndvi': 'ndvi',
  'rain': 'lluvia',
  'light': 'luz',
  'nutrients': 'nutrientes',
  'vpd': 'vpd',
  'other': 'otro'
};
```

### 7.2 Rangos Genéricos

```typescript
const genericRanges = {
  'humedad_suelo': { min: 20, max: 30, unit: '%' },
  'temperatura_aire': { min: 18, max: 30, unit: '°C' },
  'temperatura_suelo': { min: 15, max: 25, unit: '°C' },
  'humedad_aire': { min: 50, max: 80, unit: '%' },
  'ph_suelo': { min: 6.0, max: 7.5, unit: 'pH' },
  'ce': { min: 0.8, max: 2.5, unit: 'dS/m' },
  'ndvi': { min: 0.5, max: 0.9, unit: '' },
  'vpd': { min: 0.8, max: 1.5, unit: 'kPa' },
  
  // Sin rangos confiables
  'luz': null,
  'lluvia': null,
  'nutrientes': null
};
```

---

## 8. Ejemplos de Uso

### 8.1 Fetch Vanilla JavaScript

```javascript
// Chat simple
async function askQuestion(question) {
  const response = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      crop: 'tomate',
      length: 'short'
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}

// Sensor con recomendación
async function getSensorRecommendation(parameter, value, unit) {
  const response = await fetch('https://tu-api.vercel.app/v1/agro/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      parameter,
      value,
      unit,
      crop: 'tomate',
      stage: 'floración',
      length: 'short'
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}

// Uso
askQuestion('¿Cómo regar tomates?')
  .then(data => console.log(data.answer))
  .catch(console.error);

getSensorRecommendation('humedad_suelo', 35.5, '%')
  .then(data => {
    console.log('Acción:', data.recommendation.action);
    console.log('Rango:', data.recommendation.target_range);
  })
  .catch(console.error);
```

### 8.2 Axios

```javascript
import axios from 'axios';

const API = axios.create({
  baseURL: 'https://tu-api.vercel.app',
  headers: { 'Content-Type': 'application/json' }
});

// Chat
const chat = async (question, crop = null) => {
  const { data } = await API.post('/v1/agro/chat', {
    question,
    crop,
    length: 'short'
  });
  return data;
};

// Sensor
const askSensor = async (sensorData) => {
  const { data } = await API.post('/v1/agro/ask', sensorData);
  return data;
};

// Historial (solo local)
const getHistory = async (limit = 20) => {
  const { data } = await API.get('/v1/agro/history', {
    params: { limit }
  });
  return data;
};
```

### 8.3 React Query

```jsx
import { useQuery, useMutation } from '@tanstack/react-query';

// Hook para chat
function useChatMutation() {
  return useMutation({
    mutationFn: async ({ question, crop }) => {
      const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, crop, length: 'short' })
      });
      if (!res.ok) throw new Error('Failed');
      return res.json();
    }
  });
}

// Hook para historial (solo local)
function useHistory(enabled = true) {
  return useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/v1/agro/history?limit=20');
      if (!res.ok) throw new Error('History not available');
      return res.json();
    },
    enabled,
    retry: false
  });
}

// Uso en componente
function ChatComponent() {
  const chatMutation = useChatMutation();
  const { data: history } = useHistory(isLocal);

  const handleSubmit = (question) => {
    chatMutation.mutate({ question, crop: 'tomate' });
  };

  return (/* ... */);
}
```

---

## 9. Tipos TypeScript

### 9.1 Completos

```typescript
// ============================================
// CHAT (Funciona SIEMPRE)
// ============================================

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

// ============================================
// ASK (Funciona SIEMPRE)
// ============================================

export type Parameter =
  | 'humedad_suelo'
  | 'temperatura_aire'
  | 'temperatura_suelo'
  | 'humedad_aire'
  | 'ph_suelo'
  | 'ce'
  | 'ndvi'
  | 'vpd'
  | 'lluvia'
  | 'luz'
  | 'nutrientes'
  | 'otro';

export interface AskRequest {
  question?: string;
  parameter?: Parameter;
  value?: number;
  unit?: string;
  crop?: string;
  stage?: string;
  length?: 'short' | 'medium';
  safe_mode?: boolean;
}

export interface TargetRange {
  min: number | null;
  max: number | null;
  unit: string | null;
}

export interface Recommendation {
  action: 'aumentar' | 'disminuir' | 'mantener';
  parameter: string;
  target_range: TargetRange | null;
  rationale: string;
  warnings: string[];
}

export interface AskResponse {
  answer: string;
  model: string;
  usage?: Record<string, any> | null;
  tips?: string[] | null;
  recommendation?: Recommendation | null;
}

// ============================================
// HISTORIAL (Solo Local)
// ============================================

export interface ChatHistoryItem {
  id: number;
  timestamp: string;
  endpoint: '/v1/agro/chat' | '/v1/agro/ask';
  question: string;
  crop: string | null;
  stage: string | null;
  parameter: string | null;
  value: number | null;
  unit: string | null;
  answer_preview: string;
  model: string;
  response_time_ms: number;
}

export interface HistoryResponse {
  total: number;
  chats: ChatHistoryItem[];
}

export interface StatsResponse {
  total_conversations: number;
  total_sensor_readings: number;
  top_crops: Array<{ crop: string; count: number }>;
  top_parameters: Array<{ parameter: string; count: number }>;
  avg_response_time_ms: number | null;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: ChatHistoryItem[];
}

// ============================================
// HEALTH
// ============================================

export interface HealthResponse {
  status: 'ok';
  mock_mode: boolean;
  model: string;
  history_enabled: boolean;
}
```

---

## 10. Manejo de Errores

### 10.1 Códigos HTTP

| Código | Significado | Acción |
|--------|-------------|--------|
| 200 | OK | Procesar respuesta |
| 400 | Bad Request | Mostrar detalle del error al usuario |
| 422 | Validation Error | Revisar formato de datos |
| 503 | Service Unavailable | Historial deshabilitado (normal en Vercel) |
| 502 | Bad Gateway | Error al contactar Gemini (reintentar) |

### 10.2 Manejo Robusto

```jsx
async function safeApiCall(endpoint, options) {
  try {
    const response = await fetch(endpoint, options);
    
    // Manejar historial deshabilitado (503)
    if (response.status === 503) {
      console.log('Historial no disponible en este entorno');
      return null;
    }
    
    // Otros errores
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
    
  } catch (error) {
    // Error de red
    if (error.message === 'Failed to fetch') {
      console.error('Error de conexión');
      return null;
    }
    
    // Reenviar otros errores
    throw error;
  }
}

// Uso
const data = await safeApiCall('https://api.com/v1/agro/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '...' })
});

if (data) {
  // Procesar respuesta
}
```

### 10.3 Retry con Exponential Backoff

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
      
      // No reintentar errores 4xx (cliente)
      if (response.status >= 400 && response.status < 500) {
        throw new Error(`Client error: ${response.status}`);
      }
      
    } catch (error) {
      const isLastAttempt = i === maxRetries - 1;
      if (isLastAttempt) throw error;
      
      // Esperar antes de reintentar (exponencial)
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
}
```

---

## 11. Resumen: ¿Qué Implementar?

### ✅ Para Producción en Vercel (Mínimo)

```jsx
// Solo necesitas esto:
function App() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  const handleChat = async () => {
    const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, length: 'short' })
    });
    const data = await res.json();
    setAnswer(data.answer);
  };

  return (/* UI simple */);
}
```

**Funciona en Vercel**: ✅ Sí  
**Necesita base de datos**: ❌ No  
**Complejidad**: 🟢 Baja

### 🚀 Para Desarrollo Local (Con Historial)

```jsx
function AppWithHistory() {
  const [history, setHistory] = useState([]);
  
  useEffect(() => {
    // Cargar historial al inicio
    fetch('http://localhost:8000/v1/agro/history')
      .then(res => res.json())
      .then(data => setHistory(data.chats))
      .catch(() => console.log('Sin historial'));
  }, []);

  return (/* UI con sidebar de historial */);
}
```

**Funciona en Vercel**: ❌ No  
**Funciona en Local**: ✅ Sí  
**Necesita base de datos**: ✅ Sí (SQLite automático)  
**Complejidad**: 🟡 Media

---

## 12. Checklist de Implementación

### Paso 1: Chat Simple (Obligatorio)
- [ ] Crear formulario con textarea
- [ ] Implementar POST a `/v1/agro/chat`
- [ ] Mostrar `answer` en UI
- [ ] Manejar errores 400/502
- [ ] **✅ Funciona en Vercel**

### Paso 2: Sensores (Opcional)
- [ ] Crear formulario con selects de parámetro
- [ ] Implementar POST a `/v1/agro/ask`
- [ ] Renderizar `recommendation` con colores
- [ ] Mostrar `target_range` si existe
- [ ] **✅ Funciona en Vercel**

### Paso 3: Historial (Solo Local)
- [ ] Verificar `history_enabled` en `/health`
- [ ] Implementar GET a `/v1/agro/history`
- [ ] Mostrar lista de conversaciones pasadas
- [ ] Implementar búsqueda con `/v1/agro/search`
- [ ] Mostrar estadísticas con `/v1/agro/stats`
- [ ] **❌ NO funciona en Vercel**

---

## 13. Recursos Adicionales

- 📖 [Guía de Despliegue en Vercel](./VERCEL_DEPLOYMENT.md)
- 📊 [Documentación de Historial](./HISTORY_API.md)
- 🏠 [README Principal](../README.md)

---

**Fin del documento de integración frontend.**

✨ **Recuerda**: `/chat` y `/ask` funcionan en Vercel sin problemas. El historial es solo para desarrollo local.
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