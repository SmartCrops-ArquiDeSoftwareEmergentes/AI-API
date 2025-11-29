"""
Prueba rápida del nuevo endpoint /v1/agro/chat para consultas de texto libre.
"""
import httpx
import asyncio
import json


async def test_chat_endpoint():
    base_url = "http://127.0.0.1:8000"
    
    tests = [
        {
            "name": "Pregunta general sobre riego",
            "payload": {
                "question": "¿Cómo se determina la frecuencia de riego en tomates?",
                "crop": "tomate",
                "length": "short"
            }
        },
        {
            "name": "Consulta sobre nutrientes",
            "payload": {
                "question": "Factores que afectan la absorción de nitrógeno en maíz",
                "crop": "maíz",
                "stage": "V6",
                "length": "medium"
            }
        },
        {
            "name": "Pregunta sin cultivo específico",
            "payload": {
                "question": "Estrategias para mejorar retención de agua en suelos arenosos",
                "length": "short"
            }
        }
    ]
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        for test in tests:
            print(f"\n{'='*60}")
            print(f"Test: {test['name']}")
            print(f"{'='*60}")
            
            try:
                response = await client.post(
                    "/v1/agro/chat",
                    json=test["payload"],
                    timeout=30.0
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\nModelo: {data['model']}")
                    print(f"\nRespuesta:\n{data['answer']}")
                    if data.get('tips'):
                        print(f"\nTips: {data['tips']}")
                else:
                    print(f"Error: {response.text}")
                    
            except Exception as e:
                print(f"Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())
