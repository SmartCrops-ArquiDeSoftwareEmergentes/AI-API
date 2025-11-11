from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas.requests import AskRequest
from app.schemas.responses import AskResponse, Recommendation, TargetRange
from app.utils.logger import get_logger
from app.utils.sanitize import sanitize_question, sanitize_data_preview

logger = get_logger("agro.gemini")


class GeminiClient:
    def __init__(self, prompt_path: Path):
        self.settings = get_settings()
        # Carga robusta del prompt para entornos serverless
        default_prompt = (
            "Eres un asistente educativo en agricultura. Brindas orientación general, no prescriptiva, "
            "evitando marcas, dosis exactas y pasos operativos. Te enfocas en buenas prácticas, factores a considerar, "
            "rangos típicos y sugerencias de monitoreo. Respondes en español de forma clara y concisa."
        )
        try:
            self.prompt_text = prompt_path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("No se pudo leer el archivo de prompt en %s; usando prompt por defecto.", prompt_path)
            self.prompt_text = default_prompt
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

    def _compose_adjustment_prompt(self, req: AskRequest) -> str:
        """Prompt específico para obtener una recomendación direccional estructurada en JSON."""
        pv = {
            "cultivo": req.crop,
            "parametro": req.parameter,
            "valor": req.value,
            "unidad": req.unit,
            "etapa": getattr(req, "stage", None),
            "temperatura": req.temperature,
        }
        preview = sanitize_data_preview({k: v for k, v in pv.items() if v is not None}, max_chars=800)
        instructions = (
            "Tarea: Con base en el parámetro medido y el cultivo, devuelve SOLO un JSON válido en español que indique si se debe 'aumentar', 'disminuir' o 'mantener' el parámetro, con rango objetivo orientativo, justificación breve y advertencias. "
            "Sigue exactamente el esquema indicado en la instrucción del sistema. No incluyas texto fuera del JSON." 
        )
        return (
            f"Datos: {preview}\n\n" + instructions
        )

    def _build_generation_config(self, *, length: Optional[str] = None, json_output: bool = False) -> Dict[str, Any]:
        max_tokens = 900
        temperature = 0.2
        top_p = 0.9
        if length == "short":
            max_tokens = 520
            temperature = 0.1
            top_p = 0.7
        elif length == "medium" or length is None:
            max_tokens = 900
        cfg = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 40,
            "max_output_tokens": max_tokens,
        }
        if json_output:
            cfg["response_mime_type"] = "application/json"
        return cfg

    def _safety_settings(self) -> List[Dict[str, str]]:
        # Relax safety just to block only high-likelihood harmful content, reducing false positives
        return [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

    def _heuristic_recommendation(self, req: AskRequest) -> Recommendation | None:
        """Fallback simple y seguro basado en rangos orientativos genéricos.
        No sustituye al modelo, pero mejora la UX cuando no hay JSON.
        """
        if not req.parameter or req.value is None:
            return None
        p = (req.parameter or "").lower()
        unit = req.unit
        v = req.value

        # Rangos orientativos genéricos (no prescriptivos)
        ranges: Dict[str, Dict[str, float | None]] = {
            "soil_moisture": {"min": 20.0, "max": 30.0},  # % humedad de suelo
            "air_temperature": {"min": 18.0, "max": 30.0},  # °C temperatura aire
            "soil_temperature": {"min": 15.0, "max": 25.0},  # °C temperatura suelo
            "air_humidity": {"min": 50.0, "max": 80.0},  # % humedad aire (HR)
            "soil_ph": {"min": 6.0, "max": 7.5},  # pH suelo
            "ec": {"min": 0.8, "max": 2.5},  # dS/m conductividad eléctrica
            "ndvi": {"min": 0.5, "max": 0.9},  # índice NDVI
            "vpd": {"min": 0.8, "max": 1.5},  # kPa déficit de presión de vapor
            # parámetros nuevos sin rango explícito → se dejan null para no inventar
            "light": {"min": None, "max": None},  # luz/luminosidad (depende del cultivo y sensor)
            "rain": {"min": None, "max": None},  # lluvia puntual (mm)
            "nutrients": {"min": None, "max": None},  # nivel agregado de nutrientes (muy dependiente de análisis)
        }

        r = ranges.get(p)
        if not r:
            return None
        tmin = r.get("min")
        tmax = r.get("max")
        action = "mantener"
        if tmin is not None and v < tmin:
            action = "aumentar"
        elif tmax is not None and v > tmax:
            action = "disminuir"

        rationale = []
        if tmin is not None and tmax is not None:
            rationale.append(f"El valor observado ({v}{' ' + unit if unit else ''}) se compara con un rango orientativo de {tmin}–{tmax}{' ' + unit if unit else ''}.")
        elif tmin is not None:
            rationale.append(f"El valor observado ({v}{' ' + unit if unit else ''}) se compara con un mínimo orientativo de {tmin}{' ' + unit if unit else ''}.")
        elif tmax is not None:
            rationale.append(f"El valor observado ({v}{' ' + unit if unit else ''}) se compara con un máximo orientativo de {tmax}{' ' + unit if unit else ''}.")
        else:
            rationale.append("No hay rango genérico confiable; se sugiere monitoreo adicional y contextualizar según cultivo y etapa.")

        warns = [
            "Rangos genéricos de referencia; ajustar según cultivo, etapa fenológica, tipo de suelo y sistema de manejo.",
        ]
        if p in ("light",):
            warns.append("La iluminación óptima depende de cultivo, intensidad fotosintética (PPFD) y duración; calibrar con curvas específicas.")
        if p in ("nutrients",):
            warns.append("El valor de 'nutrients' requiere desagregar tipo de nutriente y comparar con análisis de suelo y foliar.")
        if p in ("rain",):
            warns.append("La lluvia puntual debe interpretarse junto a humedad del suelo y pronóstico; no indica acción directa por sí sola.")
        if p in ("ndvi",):
            warns.append("NDVI es un índice; la acción depende del diagnóstico agronómico complementario.")

        # Mapear parámetro interno inglés→español si es necesario
        param_map = {
            "soil_moisture": "humedad_suelo",
            "air_temperature": "temperatura_aire",
            "soil_temperature": "temperatura_suelo",
            "air_humidity": "humedad_aire",
            "soil_ph": "ph_suelo",
            "ec": "ce",
            "ndvi": "ndvi",
            "rain": "lluvia",
            "vpd": "vpd",
            "other": "otro",
        }
        p_es = param_map.get(p, p)
        return Recommendation(
            action=action,
            parameter=p_es,
            target_range=TargetRange(min=tmin, max=tmax, unit=unit),
            rationale=" ".join(rationale),
            warnings=warns,
        )

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def _call_gemini_structured(self, user_prompt: str) -> Recommendation | None:
        """Solicita salida JSON y la transforma en Recommendation."""
        config = self._build_generation_config(length="short", json_output=True)
        try:
            response = self._model.generate_content(
                user_prompt,
                generation_config=config,
                safety_settings=self._safety_settings(),
            )
        except Exception as e:
            logger.exception("Gemini structured call failed: %s", e)
            raise

        # Intentar extraer JSON desde parts
        raw = None
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                first = candidates[0]
                content = getattr(first, "content", None)
                parts = getattr(content, "parts", []) if content else []
                for p in parts:
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t.strip():
                        raw = t
                        break
                    elif isinstance(p, str) and p.strip():
                        raw = p
                        break
        except Exception:
            pass
        if not raw:
            # Algunos SDK retornan directamente .text
            try:
                raw = getattr(response, "text", None)
            except Exception:
                raw = None
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except Exception:
            # Intento de limpieza mínima si viene con formateo alrededor
            try:
                raw2 = raw.strip()
                if raw2.startswith("```"):
                    raw2 = raw2.strip("`\n ")
                    if raw2.startswith("json"):
                        raw2 = raw2[4:].lstrip()
                data = json.loads(raw2)
            except Exception:
                logger.debug("Structured response is not valid JSON: %s", raw[:200])
                return None

        try:
            target = None
            tr = data.get("target_range") if isinstance(data, dict) else None
            if isinstance(tr, dict):
                target = TargetRange(min=tr.get("min"), max=tr.get("max"), unit=tr.get("unit"))

            action_raw = (data.get("action") or "").lower()
            action_map = {"increase": "aumentar", "decrease": "disminuir", "maintain": "mantener"}
            action_es = action_map.get(action_raw, action_raw)

            param_raw = (data.get("parameter") or "").lower()
            param_map = {
                "soil_moisture": "humedad_suelo",
                "air_temperature": "temperatura_aire",
                "soil_temperature": "temperatura_suelo",
                "air_humidity": "humedad_aire",
                "soil_ph": "ph_suelo",
                "ec": "ce",
                "ndvi": "ndvi",
                "rain": "lluvia",
                "vpd": "vpd",
                "other": "otro",
            }
            param_es = param_map.get(param_raw, param_raw)

            rec = Recommendation(
                action=action_es,
                parameter=param_es,
                target_range=target,
                rationale=data.get("rationale"),
                warnings=data.get("warnings"),
            )
            return rec
        except Exception as e:
            logger.debug("Failed to map structured JSON to Recommendation: %s", e)
            return None

    def ask(self, req: AskRequest) -> AskResponse:
        if req.question and len(req.question) > self.settings.max_input_chars:
            raise ValueError("La pregunta es demasiado larga. Reduce el tamaño del texto.")

        length = getattr(req, "length", None) or "medium"

        # If already in mock mode, return a deterministic demo response
        if self.settings.mock_mode:
            logger.debug("Using mock mode for response.")
            tips = [
                "Incluye datos de suelo (pH, CE, % humedad) y clima (ET0, precipitación).",
                "Especifica el estado fenológico del cultivo para recomendaciones más precisas.",
            ]
            answer = (
                "[MODO DEMO] Resumen preliminar. Agrega tu GEMINI_API_KEY en .env para respuestas reales.\n\n"
                f"Resumen: {req.question[:180]}..."
            )
            recommendation = None
            if req.parameter and req.value is not None:
                recommendation = Recommendation(
                    action="maintain",
                    parameter=req.parameter,
                    target_range=TargetRange(min=None, max=None, unit=req.unit),
                    rationale="Demo: sin modelo real, se sugiere mantener de forma conservadora.",
                    warnings=["MODO DEMO: sin análisis del modelo"],
                )
            return AskResponse(answer=answer, model=self.settings.gemini_model, usage=None, tips=tips, recommendation=recommendation)

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

        # Si se proporcionan parámetros medibles, intentar flujo estructurado primero
        if req.parameter and (req.value is not None):
            prompt = self._compose_adjustment_prompt(req)
            rec = None
            # Intento principal modelo
            try:
                rec = self._call_gemini_structured(prompt)
            except Exception:
                rec = None
            # Si falla el modelo o JSON inválido, usar heurística
            if rec is None:
                rec = self._heuristic_recommendation(req)
            # Generar además un resumen en texto breve (por si el cliente lo usa)
            text_summary = None
            if rec:
                action_es = rec.action  # Ya normalizada a español
                tr = rec.target_range
                rango = None
                if tr and (tr.min is not None or tr.max is not None):
                    if tr.min is not None and tr.max is not None:
                        rango = f"{tr.min}–{tr.max} {tr.unit or ''}".strip()
                    elif tr.min is not None:
                        rango = f">= {tr.min} {tr.unit or ''}".strip()
                    elif tr.max is not None:
                        rango = f"<= {tr.max} {tr.unit or ''}".strip()
                text_summary = (
                    f"Sugerencia: {action_es or '—'} {rec.parameter or ''}. "
                    + (f"Rango objetivo: {rango}. " if rango else "")
                    + (rec.rationale or "")
                ).strip()
                return AskResponse(
                    answer=text_summary or (rec.rationale or ""),
                    model=self.settings.gemini_model,
                    usage=None,
                    tips=None,
                    recommendation=rec,
                )
            # Si no se logró JSON válido, continuar con el flujo textual educativo

        user_prompt = self._compose_user_prompt(req)
        return self._call_gemini(user_prompt, allow_reframe=bool(getattr(req, "safe_mode", True)), length=length)
