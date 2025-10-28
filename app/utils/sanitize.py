from __future__ import annotations

import re
from typing import Any, Dict


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
_IDLIKE = re.compile(r"\b\d{6,}\b")
_URL = re.compile(r"https?://\S+")

_SENSITIVE_TERMS = [
    r"(?i)veneno",
    r"(?i)venenoso",
    r"(?i)matar",
    r"(?i)expl(osiv|osivo)",
    r"(?i)arma",
    r"(?i)químico\s+peligroso",
    r"(?i)gramoxone",
]


def _mask_basic(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _IDLIKE.sub("[id]", text)
    text = _URL.sub("[url]", text)
    for pat in _SENSITIVE_TERMS:
        text = re.sub(pat, "[término sensible]", text)
    return text


def sanitize_question(text: str, max_len: int = 2000) -> str:
    text = (text or "").strip()
    text = _mask_basic(text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def sanitize_data_preview(data: Dict[str, Any], max_chars: int = 2000) -> str:
    try:
        import json

        s = json.dumps(data, ensure_ascii=False)
    except Exception:
        return "[datos no serializables]"
    s = _mask_basic(s)
    if len(s) > max_chars:
        s = s[: max_chars - 3] + "..."
    return s
