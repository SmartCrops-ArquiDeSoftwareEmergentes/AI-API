from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Any, List, Dict


class AskResponse(BaseModel):
    answer: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    tips: Optional[List[str]] = None
