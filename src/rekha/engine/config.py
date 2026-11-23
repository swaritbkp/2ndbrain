"""Load YAML config once. REKHA_CONFIG_DIR overrides the folder (tests use the default)."""
from __future__ import annotations

import functools
import os
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[3]


def config_dir() -> Path:
    return Path(os.environ.get("REKHA_CONFIG_DIR", _ROOT / "config"))


@functools.lru_cache(maxsize=None)
def load(name: str) -> dict:
    with open(config_dir() / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def rules() -> dict:
    return load("rules")


def tax() -> dict:
    return load("tax")


def schemes() -> dict:
    return {s["code"]: s for s in load("schemes")["schemes"]}
