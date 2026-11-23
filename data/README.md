`seed.py` builds `rekha.db` deterministically (8 fictional clients, 19 lots). Each client triggers one guardrail. See docs/SPEC.md §4.
Golden expected outcomes live in `tests/test_engine_golden.py`. Treat them as the spec: if an edit breaks them, the edit is wrong.
