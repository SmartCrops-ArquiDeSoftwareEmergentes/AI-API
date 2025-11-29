"""
Script para probar los endpoints de historial con el servidor en ejecución.
Asegúrate de tener el servidor corriendo: uvicorn app.main:app --reload
"""

import requests
import json
from time import sleep

BASE_URL = "http://127.0.0.1:8000"

def test_chat_endpoint():
    """Prueba el endpoint /chat y guarda en historial."""
    print("\n🧪 Probando POST /v1/agro/chat...")
    
    data = {
        "question": "¿Cómo regar el tomate en floración?",
        "crop": "tomate",
        "stage": "floración",
        "length": "short"
    }
    
    response = requests.post(f"{BASE_URL}/v1/agro/chat", json=data)
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Respuesta: {result['answer'][:100]}...")
        print(f"   Modelo: {result['model']}")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def test_ask_with_sensor():
    """Prueba el endpoint /ask con datos de sensor."""
    print("\n🧪 Probando POST /v1/agro/ask con sensor...")
    
    data = {
        "parameter": "humedad_suelo",
        "value": 42.0,
        "unit": "%",
        "crop": "tomate",
        "stage": "floración",
        "question": "¿Está bien esta humedad?"
    }
    
    response = requests.post(f"{BASE_URL}/v1/agro/ask", json=data)
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Respuesta: {result['answer'][:100]}...")
        if result.get('recommendation'):
            rec = result['recommendation']
            print(f"   Acción: {rec['action']}")
            print(f"   Parámetro: {rec['parameter']}")
            if rec.get('target_range'):
                tr = rec['target_range']
                print(f"   Rango objetivo: {tr['min']}-{tr['max']} {tr['unit']}")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def test_history():
    """Prueba el endpoint de historial."""
    print("\n🧪 Probando GET /v1/agro/history...")
    
    response = requests.get(f"{BASE_URL}/v1/agro/history", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Total conversaciones: {result['total']}")
        for chat in result['chats'][:3]:
            print(f"   - [{chat['timestamp']}] {chat['endpoint']}: {chat['question'][:50]}...")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def test_sensor_history():
    """Prueba el endpoint de historial de sensores."""
    print("\n🧪 Probando GET /v1/agro/sensors/history...")
    
    response = requests.get(f"{BASE_URL}/v1/agro/sensors/history", params={"limit": 5})
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Total lecturas: {result['total']}")
        for reading in result['readings'][:3]:
            print(f"   - {reading['parameter']}: {reading['value']} {reading['unit']} → {reading['action']}")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def test_stats():
    """Prueba el endpoint de estadísticas."""
    print("\n🧪 Probando GET /v1/agro/stats...")
    
    response = requests.get(f"{BASE_URL}/v1/agro/stats")
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Total conversaciones: {result['total_conversations']}")
        print(f"   Total sensores: {result['total_sensor_readings']}")
        print(f"   Cultivos principales: {result['top_crops'][:3]}")
        print(f"   Tiempo promedio: {result['avg_response_time_ms']}ms")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def test_search():
    """Prueba el endpoint de búsqueda."""
    print("\n🧪 Probando GET /v1/agro/search...")
    
    response = requests.get(f"{BASE_URL}/v1/agro/search", params={"q": "tomate", "limit": 3})
    print(f"   Status: {response.status_code}")
    if response.ok:
        result = response.json()
        print(f"   ✅ Resultados para '{result['query']}': {result['total']}")
        for r in result['results'][:2]:
            print(f"   - {r['question'][:50]}...")
    else:
        print(f"   ❌ Error: {response.text}")
    
    return response.ok

def main():
    print("=" * 60)
    print("PRUEBA DE ENDPOINTS DE HISTORIAL")
    print("=" * 60)
    print("Asegúrate de tener el servidor corriendo:")
    print("  uvicorn app.main:app --reload")
    print("=" * 60)
    
    # Esperar un poco para asegurar que el servidor está listo
    sleep(1)
    
    # Verificar que el servidor está disponible
    try:
        response = requests.get(f"{BASE_URL}/health")
        if not response.ok:
            print("❌ El servidor no está disponible en", BASE_URL)
            return
        print(f"✅ Servidor disponible: {response.json()}")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("Asegúrate de ejecutar: uvicorn app.main:app --reload")
        return
    
    # Ejecutar pruebas
    results = []
    
    results.append(("Chat endpoint", test_chat_endpoint()))
    sleep(0.5)
    
    results.append(("Ask with sensor", test_ask_with_sensor()))
    sleep(0.5)
    
    results.append(("History", test_history()))
    sleep(0.5)
    
    results.append(("Sensor history", test_sensor_history()))
    sleep(0.5)
    
    results.append(("Stats", test_stats()))
    sleep(0.5)
    
    results.append(("Search", test_search()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 Todas las pruebas pasaron!" if all_passed else "⚠️ Algunas pruebas fallaron"))

if __name__ == "__main__":
    main()
