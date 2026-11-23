# state/<phase>.json
```json
{"phase":"02-baseline-runner","status":"PASS|DEGRADED|FAIL|STOP","summary":"what was built and verified",
 "tests":{"passed":0,"failed":0},"artifacts":["paths"],"degraded_items":["what's missing and why"],
 "review":{"verdict":"PROCEED|FIX_FIRST","blockers":0,"notes":"..."},"ts":"ISO-8601"}
```
PASS = acceptance met + reviewer PROCEED. DEGRADED = core met, EDGE items missing (listed). FAIL = core not met. STOP = hard stop (write STOPPED.md too).
The driver runs `scripts/verify_phase.py <phase>` afterwards: if that fails, the phase is treated as FAIL whatever this file says.
