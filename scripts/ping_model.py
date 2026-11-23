"""One tiny tool-calling request per resolved model. Exit 0 if the arena model returned a tool call."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from openai import OpenAI  # noqa: E402

from rekha.arena import models  # noqa: E402

TOOLS = [{"type": "function", "function": {"name": "get_time", "description": "Get the current time",
          "parameters": {"type": "object", "properties": {}, "required": []}}}]


def ping(model: str) -> bool:
    client = OpenAI(**models.client_kwargs())
    for attempt in range(3):
        try:
            r = client.chat.completions.create(model=model, tools=TOOLS, max_tokens=800,
                                               messages=[{"role": "user", "content": "Call the get_time tool now."}])
            calls = r.choices[0].message.tool_calls or []
            print(f"{model}: tool_calls={len(calls)}")
            return bool(calls)
        except Exception as e:
            print(f"{model}: attempt {attempt + 1} failed: {type(e).__name__}: {str(e)[:300]}")
            time.sleep(5 * (attempt + 1))
    return False


if __name__ == "__main__":
    ok = ping(models.get("arena"))
    for extra in [models.get("attacker")] + [m for m in models.get("sweep").split(",") if m]:
        if extra:
            ping(extra)
    sys.exit(0 if ok else 1)
