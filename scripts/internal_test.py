from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app

client = TestClient(app)

# Health check
r = client.get("/health")
print("/health status:", r.status_code, r.json())

# Real ask (respects settings from .env)
payload = {
    "question": "Como ejemplo teórico, describe pautas generales de riego en maíz en etapa vegetativa con clima templado, en tono no prescriptivo y sin productos.",
    "crop": "maíz",
    "temperature": 25,
    "safe_mode": True
}
r = client.post("/v1/agro/ask", json=payload)
print("/v1/agro/ask status:", r.status_code)
try:
    print(r.json())
except Exception:
    print(r.text)
