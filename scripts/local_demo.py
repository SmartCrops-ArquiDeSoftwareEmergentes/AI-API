from pathlib import Path
import sys

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas.requests import AskRequest
from app.services.gemini_client import GeminiClient

if __name__ == "__main__":
    prompt_path = Path(__file__).resolve().parent.parent / "app" / "prompts" / "agriculture_system_prompt.md"
    client = GeminiClient(prompt_path)
    req = AskRequest(
        question="Tengo tomate con manchas foliares y baja humedad de suelo. ¿Qué hago?",
        crop="tomate",
        location="La Libertad, PE",
        data={"suelo": {"pH": 6.5, "humedad_pct": 15}, "clima": {"temp": 27, "lluvia_mm": 0}},
        language="es",
    )
    resp = client.ask(req)
    print({"model": resp.model, "answer": resp.answer[:200] + ("..." if len(resp.answer) > 200 else "")})
