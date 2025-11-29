# 💬 Chat API - Guía Rápida

## 🎯 Resumen en 30 Segundos

El endpoint `/v1/agro/chat` te permite crear un chatbot agrícola simple:
- ✅ **Funciona en Vercel** (sin base de datos)
- ✅ **Funciona en Local** (con o sin historial)
- ✅ **Solo necesitas**: pregunta de texto libre
- ✅ **Respuesta**: texto educativo en español

---

## 🚀 Ejemplo Mínimo

### JavaScript Vanilla

```javascript
async function preguntarAlChat(pregunta) {
  const response = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: pregunta,
      length: 'short'
    })
  });
  
  const data = await response.json();
  return data.answer; // Respuesta en texto
}

// Uso
preguntarAlChat('¿Cómo regar el tomate en verano?')
  .then(respuesta => console.log(respuesta));
```

### React

```jsx
function ChatBot() {
  const [pregunta, setPregunta] = useState('');
  const [respuesta, setRespuesta] = useState('');
  const [cargando, setCargando] = useState(false);

  const enviarPregunta = async (e) => {
    e.preventDefault();
    setCargando(true);

    try {
      const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: pregunta,
          crop: 'tomate',      // Opcional
          length: 'short'      // 'short' o 'medium'
        })
      });

      const data = await res.json();
      setRespuesta(data.answer);
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="chatbot">
      <form onSubmit={enviarPregunta}>
        <textarea
          value={pregunta}
          onChange={(e) => setPregunta(e.target.value)}
          placeholder="Escribe tu pregunta..."
          rows={4}
        />
        <button type="submit" disabled={cargando}>
          {cargando ? 'Pensando...' : 'Preguntar'}
        </button>
      </form>

      {respuesta && (
        <div className="respuesta">
          {respuesta}
        </div>
      )}
    </div>
  );
}
```

---

## 📋 Request Schema

```typescript
interface ChatRequest {
  question: string;              // REQUERIDO: Tu pregunta
  crop?: string;                 // Opcional: "tomate", "maíz", etc.
  stage?: string;                // Opcional: "floración", "vegetativo"
  length?: 'short' | 'medium';   // Opcional: default 'medium'
  safe_mode?: boolean;           // Opcional: default true
}
```

### Ejemplos de Request

```javascript
// Mínimo
{ "question": "¿Cómo regar el tomate?" }

// Con contexto de cultivo
{
  "question": "¿Cuándo cosechar?",
  "crop": "tomate",
  "stage": "fructificación"
}

// Respuesta corta
{
  "question": "Síntomas de exceso de riego",
  "crop": "lechuga",
  "length": "short"
}

// Pregunta general (sin cultivo específico)
{
  "question": "Diferencia entre suelo arenoso y arcilloso",
  "length": "medium"
}
```

---

## 📤 Response Schema

```typescript
interface ChatResponse {
  answer: string;    // Respuesta en texto con bullets (•)
  model: string;     // Modelo usado: "gemini-2.5-flash"
  tips?: string[];   // Tips adicionales (puede ser null)
}
```

### Ejemplo de Response

```json
{
  "answer": "El riego del tomate durante el verano requiere:\n\n• Frecuencia: 2-3 veces por semana en clima cálido\n• Cantidad: Mantener humedad constante sin encharcamiento\n• Momento: Preferiblemente temprano en la mañana\n• Método: Riego por goteo es ideal para conservar agua",
  "model": "gemini-2.5-flash",
  "tips": [
    "Evitar mojar las hojas para prevenir enfermedades",
    "Usar mulch para retener humedad"
  ]
}
```

---

## 🎨 Renderizado de Respuestas

Las respuestas vienen con bullets (`•`) que puedes convertir en listas HTML:

```jsx
function RenderRespuesta({ answer }) {
  const lineas = answer.split('\n');
  
  return (
    <div className="respuesta">
      {lineas.map((linea, i) => {
        if (linea.trim().startsWith('•')) {
          return (
            <li key={i}>
              {linea.replace('•', '').trim()}
            </li>
          );
        }
        return <p key={i}>{linea}</p>;
      })}
    </div>
  );
}
```

### CSS Sugerido

```css
.chatbot {
  max-width: 600px;
  margin: 2rem auto;
  padding: 1.5rem;
  border-radius: 8px;
  background: #f9f9f9;
}

textarea {
  width: 100%;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  resize: vertical;
}

button {
  margin-top: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.respuesta {
  margin-top: 1.5rem;
  padding: 1rem;
  background: white;
  border-left: 4px solid #28a745;
  border-radius: 4px;
  line-height: 1.6;
}

.respuesta li {
  margin-left: 1.5rem;
  margin-bottom: 0.5rem;
}
```

---

## 🔄 Chat con Historial de Sesión

Para mantener conversaciones en memoria (solo durante la sesión):

```jsx
function ChatConHistorial() {
  const [mensajes, setMensajes] = useState([]);
  const [preguntaActual, setPreguntaActual] = useState('');
  const [cargando, setCargando] = useState(false);

  const enviarMensaje = async (e) => {
    e.preventDefault();
    if (!preguntaActual.trim()) return;

    setCargando(true);

    try {
      const res = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: preguntaActual,
          length: 'short'
        })
      });

      const data = await res.json();

      // Agregar pregunta y respuesta al historial
      setMensajes([
        ...mensajes,
        {
          tipo: 'pregunta',
          texto: preguntaActual,
          timestamp: new Date()
        },
        {
          tipo: 'respuesta',
          texto: data.answer,
          timestamp: new Date()
        }
      ]);

      setPreguntaActual('');
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="chat-container">
      {/* Historial de mensajes */}
      <div className="chat-historial">
        {mensajes.map((msg, i) => (
          <div key={i} className={`mensaje ${msg.tipo}`}>
            <small>{msg.timestamp.toLocaleTimeString()}</small>
            <p>{msg.texto}</p>
          </div>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={enviarMensaje} className="chat-input">
        <textarea
          value={preguntaActual}
          onChange={(e) => setPreguntaActual(e.target.value)}
          placeholder="Escribe tu pregunta..."
          rows={2}
        />
        <button type="submit" disabled={cargando}>
          {cargando ? '⏳' : '📤'} Enviar
        </button>
      </form>
    </div>
  );
}
```

### CSS para Chat

```css
.chat-container {
  max-width: 700px;
  margin: 2rem auto;
  height: 600px;
  display: flex;
  flex-direction: column;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.chat-historial {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f5f5f5;
}

.mensaje {
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 8px;
  max-width: 80%;
}

.mensaje.pregunta {
  background: #007bff;
  color: white;
  margin-left: auto;
  text-align: right;
}

.mensaje.respuesta {
  background: white;
  border-left: 4px solid #28a745;
}

.mensaje small {
  opacity: 0.7;
  font-size: 0.75rem;
}

.chat-input {
  padding: 1rem;
  background: white;
  border-top: 1px solid #ddd;
  display: flex;
  gap: 0.5rem;
}

.chat-input textarea {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 0.5rem;
  resize: none;
}

.chat-input button {
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
```

---

## ⚠️ Manejo de Errores

```javascript
async function chatSeguro(pregunta) {
  try {
    const response = await fetch('https://tu-api.vercel.app/v1/agro/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: pregunta, length: 'short' })
    });

    // Error 400: Pregunta inválida
    if (response.status === 400) {
      const error = await response.json();
      throw new Error(error.detail || 'Pregunta demasiado larga');
    }

    // Error 502: Servicio no disponible
    if (response.status === 502) {
      throw new Error('Servicio temporalmente no disponible. Intenta de nuevo.');
    }

    // Otros errores
    if (!response.ok) {
      throw new Error(`Error ${response.status}`);
    }

    const data = await response.json();
    return data.answer;

  } catch (error) {
    // Error de red
    if (error.message === 'Failed to fetch') {
      throw new Error('Sin conexión a internet');
    }
    throw error;
  }
}
```

---

## 📊 Ejemplos de Preguntas

### Cultivos Específicos
```javascript
"¿Cómo regar el tomate en verano?"
"¿Cuándo plantar maíz en zona templada?"
"Síntomas de deficiencia de nitrógeno en lechuga"
"¿Cómo controlar plagas en fresa orgánicamente?"
```

### Manejo de Suelo
```javascript
"Diferencia entre suelo arenoso y arcilloso"
"¿Cómo mejorar retención de agua en suelo?"
"¿Qué es la conductividad eléctrica del suelo?"
```

### Técnicas de Cultivo
```javascript
"Ventajas de hidroponía vs suelo"
"¿Qué es el mulching y para qué sirve?"
"Diferencia entre riego por goteo y aspersión"
```

### Problemas Comunes
```javascript
"¿Por qué mis plantas tienen hojas amarillas?"
"Síntomas de exceso de riego"
"¿Cómo prevenir enfermedades en invernadero?"
```

---

## 🔧 Configuración de URLs

### Desarrollo Local
```javascript
const API_URL = 'http://localhost:8000';
```

### Producción (Vercel)
```javascript
const API_URL = 'https://tu-proyecto.vercel.app';
```

### Variable de Entorno (Recomendado)
```javascript
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

En `.env`:
```bash
REACT_APP_API_URL=https://tu-proyecto.vercel.app
```

---

## 🌐 Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://tu-api.vercel.app',
  headers: { 'Content-Type': 'application/json' }
});

async function chat(question, crop = null, length = 'short') {
  try {
    const { data } = await api.post('/v1/agro/chat', {
      question,
      crop,
      length
    });
    return data.answer;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Error del servidor');
    }
    throw new Error('Error de conexión');
  }
}

// Uso
chat('¿Cómo regar tomates?', 'tomate')
  .then(respuesta => console.log(respuesta))
  .catch(error => console.error(error.message));
```

---

## 🎯 Diferencia: Chat vs Ask

| Feature | `/v1/agro/chat` | `/v1/agro/ask` |
|---------|-----------------|----------------|
| **Uso** | Preguntas generales | Datos de sensores |
| **Input** | Solo texto | Parámetro + valor |
| **Output** | Texto educativo | Recomendación estructurada |
| **Ideal para** | Chatbot, FAQ | Dashboard IoT |
| **Ejemplo** | "¿Cómo regar?" | `{parameter: "humedad_suelo", value: 35}` |

### Cuándo usar cada uno

**Usa `/chat` si:**
- ✅ Usuario escribe en lenguaje natural
- ✅ No tienes datos de sensores
- ✅ Quieres un textbox simple

**Usa `/ask` si:**
- ✅ Tienes lecturas de sensores
- ✅ Necesitas recomendación estructurada (aumentar/disminuir)
- ✅ Quieres rangos objetivo

---

## ✅ Checklist de Implementación

- [ ] Crear formulario con textarea
- [ ] Conectar a `/v1/agro/chat`
- [ ] Mostrar respuesta en UI
- [ ] Manejar estado de carga
- [ ] Manejar errores (400, 502)
- [ ] Agregar validación de input
- [ ] Opcional: historial en memoria
- [ ] Opcional: renderizar bullets como lista
- [ ] Probar en desarrollo local
- [ ] Probar en Vercel

---

## 🚀 Deploy

### Variables de Entorno en Vercel

```bash
GEMINI_API_KEY = tu_clave_real
MOCK_MODE = false
ENABLE_HISTORY = false  # No necesario para chat
```

El endpoint `/chat` funciona perfectamente sin historial.

---

## 📚 Recursos

- [Documentación Completa de Frontend](./FRONTEND_INTEGRATION.md)
- [Guía de Despliegue en Vercel](./VERCEL_DEPLOYMENT.md)
- [Endpoint Ask con Sensores](./FRONTEND_INTEGRATION.md#5-implementación-avanzada-ask-con-sensores)

---

**¡Listo para usar!** 🎉

El endpoint `/chat` es todo lo que necesitas para crear un chatbot agrícola funcional en producción.
