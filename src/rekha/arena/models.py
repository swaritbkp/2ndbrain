"""Resolve which OpenRouter models to use. state/models.json (written by scripts/openrouter_models.py) wins over .env
only when the .env choice failed validation, and every substitution is recorded there."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def _state() -> dict:
    p = ROOT / "state" / "models.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def get(role: str) -> str:
    """role: arena | attacker | synapse | sweep (comma list)."""
    st = _state().get("resolved", {})
    env = {"arena": "ARENA_MODEL", "attacker": "ATTACKER_MODEL", "synapse": "SYNAPSE_MODEL", "sweep": "ARENA_SWEEP_MODELS"}[role]
    return st.get(role) or os.environ.get(env, "") or (get("arena") if role == "attacker" else "")


def client_kwargs() -> dict:
    return {"base_url": os.environ.get("ARENA_BASE_URL", "https://openrouter.ai/api/v1"),
            "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
            "default_headers": {"X-Title": "Lakshman Rekha arena"}}
