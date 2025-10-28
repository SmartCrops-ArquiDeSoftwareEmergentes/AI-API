import asyncio
import json

import httpx


async def main():
    base = "http://127.0.0.1:8000"

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"{base}/health")
            r.raise_for_status()
        except Exception:
            print("No se pudo conectar al servidor. Inicia el API con: uvicorn app.main:app --reload --port 8000")
            return

        payload = {
            "question": "Tengo maíz en V6 con hojas amarillas en bordes. ¿Qué hago?",
            "crop": "maíz",
            "temperature": 28
        }
        r = await client.post(f"{base}/v1/agro/ask", json=payload)
        print("Status:", r.status_code)
        try:
            print(json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception:
            print(r.text)


if __name__ == "__main__":
    asyncio.run(main())
