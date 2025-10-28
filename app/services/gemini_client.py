from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse
from app.utils.logger import get_logger
from app.utils.sanitize import sanitize_question, sanitize_data_preview

logger = get_logger("agro.gemini")


class GeminiClient:
    def __init__(self, prompt_path: Path):
        self.settings = get_settings()
        self.prompt_text = prompt_path.read_text(encoding="utf-8")
        self._model = None
        self._configured = False

    def _configure(self):
        if self._configured:
            return
        if not self.settings.mock_mode and not self.settings.gemini_api_key:
            logger.warning("No GEMINI_API_KEY provided. Falling back to mock mode.")
            self.settings.mock_mode = True
            return
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.gemini_api_key)
            # Determine best available model for generateContent
            requested = (self.settings.gemini_model or "").strip()
            normalized = requested.replace("-latest", "") if requested.endswith("-latest") else requested
            # Prefer 2.5 family if available
            preferences = [
                normalized,
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]

            try:
                models = list(genai.list_models())
                avail = {
                    getattr(m, "name", "").split("/")[-1]
                    for m in models
                    if "supported_generation_methods" in dir(m)
                    and "generateContent" in getattr(m, "supported_generation_methods", [])
                }
            except Exception:
                avail = set()

            candidates = [m for m in preferences if m] or ["gemini-2.5-flash"]
            if avail:
                candidates = [m for m in candidates if m in avail] or list(avail)

            last_err = None
            for m in candidates:
                try:
                    self._model = genai.GenerativeModel(
                        model_name=m,
                        system_instruction=self.prompt_text,
                    )
                    self.settings.gemini_model = m
                    break
                except Exception as e:  # try next candidate
                    last_err = e
                    continue
            if self._model is None:
                raise last_err or RuntimeError("No se pudo configurar el modelo de Gemini.")
            self._genai = genai
            self._configured = True
            logger.info("Gemini client configured with model %s", self.settings.gemini_model)
        except Exception as e:
            logger.exception("Failed to configure Gemini: %s", e)
            self.settings.mock_mode = True

    def _compose_user_prompt(self, req: AskRequest) -> str:
        parts: List[str] = []
        # Educational, non-prescriptive framing to reduce safety blocks
        parts.append(
            "Contexto educativo: Esta consulta es únicamente informativa y de ejemplo teórico para agricultura. "
            "No contiene datos personales ni requiere instrucciones operativas. Evita nombres comerciales o marcas; no incluyas cantidades numéricas, calendarios ni instrucciones paso a paso. "
            "Responde en tono no prescriptivo (""podría"", ""en general"", ""como referencia"") y con foco en buenas prácticas."
        )
        if req.crop:
            parts.append(f"Cultivo: {req.crop}")
        safe_q = sanitize_question(req.question, max_len=min(800, self.settings.max_input_chars))
        parts.append(f"Pregunta: {safe_q}")
        if getattr(req, "temperature", None) is not None:
            parts.append(f"Temperatura (°C): {req.temperature}")
        # Gentle instruction on output style
        parts.append(
            "Formato de salida: \n"
            "- 1) Resumen educativo breve\n"
            "- 2) Pautas generales (bullets, no prescripciones)\n"
            "- 3) Parámetros de referencia (rangos típicos)\n"
            "- 4) Monitoreo sugerido\n"
            "- 5) Riesgos y mitigaciones generales\n"
            "- 6) Datos extra útiles (si aplican)"
        )
        # Length guidance (parametrized)
        length = getattr(req, "length", None) or "medium"
        if length == "short":
            parts.append(
                "Longitud sugerida: 3–5 bullets concisos (~150–220 palabras). "
                "Evita pasos operativos, imperativos o detalles numéricos."
            )
        else:
            parts.append(
                "Mantén la respuesta concisa (≈ 200–350 palabras) y enfocada en bullets; evita redundancias."
            )
        return "\n\n".join(parts)

    def _build_generation_config(self, *, length: Optional[str] = None) -> Dict[str, Any]:
        max_tokens = 900
        temperature = 0.2
        top_p = 0.9
        if length == "short":
            max_tokens = 520
            temperature = 0.1
            top_p = 0.7
        elif length == "medium" or length is None:
            max_tokens = 900
        return {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 40,
            "max_output_tokens": max_tokens,
        }

    def _safety_settings(self) -> List[Dict[str, str]]:
        # Relax safety just to block only high-likelihood harmful content, reducing false positives
        return [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def _call_gemini(self, user_prompt: str, *, allow_reframe: bool = True, length: Optional[str] = None) -> AskResponse:
        config = self._build_generation_config(length=length)
        try:
            response = self._model.generate_content(
                user_prompt,
                generation_config=config,
                safety_settings=self._safety_settings(),
            )
        except Exception as e:
            msg = str(e).lower()
            # Fallback to a widely available model if the requested one isn't supported
            if "404" in msg or "not found" in msg or "unsupported" in msg:
                try:
                    import google.generativeai as genai

                    fallback = "gemini-1.5-flash"
                    logger.info("Falling back to model %s due to availability error", fallback)
                    self._model = genai.GenerativeModel(
                        model_name=fallback,
                        system_instruction=self.prompt_text,
                    )
                    self.settings.gemini_model = fallback
                    response = self._model.generate_content(
                        user_prompt,
                        generation_config=config,
                        safety_settings=self._safety_settings(),
                    )
                except Exception as e2:
                    logger.exception("Gemini fallback call failed: %s", e2)
                    raise e2
            else:
                logger.exception("Gemini call failed: %s", e)
                raise

        # Extract answer text robustly without accessing response.text property
        answer = ""
        finish_reason = None
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                first = candidates[0]
                content = getattr(first, "content", None)
                parts = getattr(content, "parts", []) if content else []
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t:
                        texts.append(t)
                    elif isinstance(p, str) and p:
                        texts.append(p)
                answer = "\n".join(texts)
                finish_reason = getattr(first, "finish_reason", None)
                if not answer and finish_reason not in (None, 0):
                    answer = (
                        "La respuesta fue bloqueada por las políticas de seguridad del modelo. "
                        "Intenta reformular la pregunta con términos neutros y sin información sensible."
                    )
        except Exception:
            pass
        usage_md = getattr(response, "usage_metadata", None)
        usage = None
        if usage_md:
            # Best-effort conversion to dict
            usage = {
                k: getattr(usage_md, k)
                for k in dir(usage_md)
                if not k.startswith("_") and not callable(getattr(usage_md, k))
            }
        # If blocked or empty, try a single educational reframe to reduce safety triggers
        if allow_reframe and (not answer or "fue bloqueada" in answer.lower() or finish_reason not in (None, 0)):
            try:
                re_user_prompt = (
                    user_prompt
                    + "\n\nReformulación: Proporciona únicamente un resumen educativo general de alto nivel. "
                      "Evita pasos operativos, cantidades, dosis, calendarios o imperativos. "
                      "No incluyas productos, marcas ni instrucciones de ‘cómo hacer’. "
                      "En su lugar, resume factores a considerar, buenas prácticas generales y señales de monitoreo, usando lenguaje condicional. "
                      "No apliques límites de longitud estrictos; prioriza neutralidad y claridad (≈150–300 palabras en bullets)."
                )
                response2 = self._model.generate_content(
                    re_user_prompt,
                    generation_config={**config, "temperature": 0.1, "top_p": 0.7},
                    safety_settings=self._safety_settings(),
                )
                # Extract again
                answer2 = ""
                try:
                    candidates2 = getattr(response2, "candidates", None) or []
                    if candidates2:
                        first2 = candidates2[0]
                        content2 = getattr(first2, "content", None)
                        parts2 = getattr(content2, "parts", []) if content2 else []
                        texts2 = []
                        for p in parts2:
                            t2 = getattr(p, "text", None)
                            if isinstance(t2, str) and t2:
                                texts2.append(t2)
                            elif isinstance(p, str) and p:
                                texts2.append(p)
                        answer2 = "\n".join(texts2)
                except Exception:
                    pass
                if answer2:
                    answer = answer2
            except Exception:
                pass

            # Second, more generic reframe if still empty/blocked
            if not answer:
                try:
                    re_user_prompt2 = (
                        "Finalidad educativa: Ofrece un panorama general sobre manejo del agua en cultivos en términos amplios y neutros. "
                        "Evita pasos operativos, cantidades, dosis, calendarios, marcas o productos. "
                        "Usa bullets y lenguaje condicional para describir factores a considerar (clima, suelo, fenología, monitoreo), sin recomendaciones prescriptivas."
                    )
                    response3 = self._model.generate_content(
                        re_user_prompt2,
                        generation_config={**config, "temperature": 0.1, "top_p": 0.6},
                        safety_settings=self._safety_settings(),
                    )
                    answer3 = ""
                    try:
                        candidates3 = getattr(response3, "candidates", None) or []
                        if candidates3:
                            first3 = candidates3[0]
                            content3 = getattr(first3, "content", None)
                            parts3 = getattr(content3, "parts", []) if content3 else []
                            texts3 = []
                            for p in parts3:
                                t3 = getattr(p, "text", None)
                                if isinstance(t3, str) and t3:
                                    texts3.append(t3)
                                elif isinstance(p, str) and p:
                                    texts3.append(p)
                            answer3 = "\n".join(texts3)
                    except Exception:
                        pass
                    if answer3:
                        answer = answer3
                except Exception:
                    pass

            # Third fallback: if requested short still fails, try concise-medium guidance
            if not answer and (length == "short"):
                try:
                    re_user_prompt3 = (
                        user_prompt
                        + "\n\nAjuste de formato: Responde de forma concisa (≈ 200–300 palabras) en bullets educativos. "
                          "Evita pasos, cantidades numéricas, calendarios, marcas o productos. Usa lenguaje condicional."
                    )
                    response4 = self._model.generate_content(
                        re_user_prompt3,
                        generation_config=self._build_generation_config(length="medium"),
                        safety_settings=self._safety_settings(),
                    )
                    answer4 = ""
                    try:
                        candidates4 = getattr(response4, "candidates", None) or []
                        if candidates4:
                            first4 = candidates4[0]
                            content4 = getattr(first4, "content", None)
                            parts4 = getattr(content4, "parts", []) if content4 else []
                            texts4 = []
                            for p in parts4:
                                t4 = getattr(p, "text", None)
                                if isinstance(t4, str) and t4:
                                    texts4.append(t4)
                                elif isinstance(p, str) and p:
                                    texts4.append(p)
                            answer4 = "\n".join(texts4)
                    except Exception:
                        pass
                    if answer4:
                        answer = answer4
                except Exception:
                    pass

        return AskResponse(answer=answer.strip(), model=self.settings.gemini_model, usage=usage, tips=None)

    def ask(self, req: AskRequest) -> AskResponse:
        if len(req.question) > self.settings.max_input_chars:
            raise ValueError("La pregunta es demasiado larga. Reduce el tamaño del texto.")

        user_prompt = self._compose_user_prompt(req)
        length = getattr(req, "length", None) or "medium"

        # If already in mock mode, return a deterministic demo response
        if self.settings.mock_mode:
            logger.debug("Using mock mode for response.")
            tips = [
                "Incluye datos de suelo (pH, CE, % humedad) y clima (ET0, precipitación).",
                "Especifica el estado fenológico del cultivo para recomendaciones más precisas.",
            ]
            answer = (
                "[MODO DEMO] Recomendación preliminar para agricultura basada en la información disponible. "
                "Agrega tu GEMINI_API_KEY en .env para respuestas reales.\n\n"
                f"Resumen: {req.question[:180]}...\n\n"
                "Siguiente paso: proporciona datos de suelo y clima para ajustar dosis y calendario."
            )
            return AskResponse(answer=answer, model=self.settings.gemini_model, usage=None, tips=tips)

        # Ensure client is configured; on failure, configuration can toggle mock_mode
        self._configure()
        if self.settings.mock_mode:
            # If configuration failed and switched to mock mode, return mock response now
            logger.debug("Configuration switched to mock mode; returning demo response.")
            tips = [
                "Incluye datos de suelo (pH, CE, % humedad) y clima (ET0, precipitación).",
                "Especifica el estado fenológico del cultivo para recomendaciones más precisas.",
            ]
            answer = (
                "[MODO DEMO] Recomendación preliminar para agricultura basada en la información disponible. "
                "Agrega tu GEMINI_API_KEY en .env para respuestas reales.\n\n"
                f"Resumen: {req.question[:180]}...\n\n"
                "Siguiente paso: proporciona datos de suelo y clima para ajustar dosis y calendario."
            )
            return AskResponse(answer=answer, model=self.settings.gemini_model, usage=None, tips=tips)

        return self._call_gemini(user_prompt, allow_reframe=bool(getattr(req, "safe_mode", True)), length=length)
