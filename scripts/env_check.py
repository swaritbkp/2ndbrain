"""Print SET/UNSET for env keys (never values). Exit 1 if a required key is missing."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
REQUIRED = ["OPENROUTER_API_KEY", "ARENA_MODEL", "REKHA_TOKEN_SECRET"]
OPTIONAL = ["ATTACKER_MODEL", "ARENA_SWEEP_MODELS", "SYNAPSE_MODEL", "SYNAPSE_MODEL_FALLBACKS", "OPENAI_API_KEY"]
missing = [k for k in REQUIRED if not os.environ.get(k, "").strip()]
for k in REQUIRED + OPTIONAL:
    print(f"{k}: {'SET' if os.environ.get(k, '').strip() else 'UNSET'}{' (required)' if k in REQUIRED else ''}")
if os.environ.get("REKHA_TOKEN_SECRET", "") in ("", "change-me-long-random-string"):
    print("WARNING: REKHA_TOKEN_SECRET is the default placeholder")
sys.exit(1 if missing else 0)
