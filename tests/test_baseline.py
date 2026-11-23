"""Fairness: the baseline exposes exactly the 12 engine functions, with docstrings verbatim."""
from __future__ import annotations

import inspect

from mcp_client import list_tools
from rekha.engine import functions as F


def test_fastapi_routes_mirror_engine():
    from rekha.baseline.api import app
    routes = {r.name: r for r in app.routes if getattr(r, "endpoint", None) and r.name in F.PUBLIC_FUNCTIONS}
    assert set(routes) == set(F.PUBLIC_FUNCTIONS)
    for name, r in routes.items():
        assert inspect.getdoc(r.endpoint) == inspect.getdoc(getattr(F, name)), name


def test_sdk_server_exposes_12_tools_with_docstrings(db):
    tools = {t["name"]: t for t in list_tools("rekha.baseline.sdk_server")}
    assert set(tools) == set(F.PUBLIC_FUNCTIONS)
    for name, t in tools.items():
        assert t["description"].strip() == getattr(F, name).__doc__.strip()
