#!/usr/bin/env bash
# Lakshman Rekha: unattended build driver (macOS/Linux/Git Bash). Mirrors run_autonomous.ps1.
# Usage: ./run_autonomous.sh [--full-auto] [--start N] [--force] [--dry-run]
set -u
cd "$(dirname "$0")"
MODEL="${REKHA_CLAUDE_MODEL:-claude-opus-5-5}"; START=0; FULL=0; FORCE=0; DRY=0; SLEEP_MIN=20; MAX_SLEEPS=9
while [ $# -gt 0 ]; do case "$1" in --full-auto) FULL=1;; --force) FORCE=1;; --dry-run) DRY=1;; --start) START="$2"; shift;; *) echo "unknown $1"; exit 1;; esac; shift; done
# id:critical:attempts:turns:minutes
PHASES=("00-preflight:1:3:80:45" "01-compose:1:3:200:120" "02-baseline-runner:1:3:300:180" "03-viewer:0:2:200:90" "04-arena:1:3:250:360" "05-distinctive:0:2:300:240" "06-submission:0:2:300:180")
mkdir -p state logs
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python; [ -x .venv/Scripts/python.exe ] && PY=.venv/Scripts/python.exe
say(){ l="$(date '+%Y-%m-%d %H:%M:%S') [driver] $*"; echo "$l"; echo "- $l" >> PROGRESS.md; }
status(){ f="state/$1.json"; [ -f "$f" ] || { echo MISSING; return; }; "$PY" -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8-sig')).get('status','UNREADABLE'))" "$f" 2>/dev/null || echo UNREADABLE; }
setfail(){ "$PY" - "$1" "$2" <<'PYEOF'
import json,sys,os
f=f"state/{sys.argv[1]}.json"; o={}
if os.path.exists(f):
    try: o=json.load(open(f,encoding='utf-8-sig'))
    except Exception: o={}
o["status"]="FAIL"; o["driver_note"]=sys.argv[2]; o.setdefault("phase",sys.argv[1])
json.dump(o,open(f,"w",encoding="utf-8"),indent=2)
PYEOF
}
command -v claude >/dev/null || { echo "claude CLI not found"; exit 1; }
[ -f .env ] || { echo ".env missing: copy .env.example to .env and fill in the keys"; exit 1; }
if [ $DRY -eq 1 ]; then for p in "${PHASES[@]}"; do echo "$p status=$(status "${p%%:*}")"; done; exit 0; fi
rm -f STOPPED.md; sleeps=0; say "run started (model=$MODEL full=$FULL start=$START)"
for ((i=START; i<${#PHASES[@]}; i++)); do
  IFS=: read -r id critical attempts turns minutes <<< "${PHASES[$i]}"
  st=$(status "$id"); if [ $FORCE -eq 0 ] && { [ "$st" = PASS ] || [ "$st" = DEGRADED ]; }; then say "skip $id ($st)"; continue; fi
  a=0; done_=0
  while [ $done_ -eq 0 ] && [ $a -lt "$attempts" ]; do
    a=$((a+1))
    prompt="You are running UNATTENDED: no human will answer until the run ends. Read CLAUDE.md, then execute .claude/commands/$id.md exactly. Never ask questions; follow docs/FALLBACKS.md and log decisions in docs/DECISIONS.md. End by writing state/$id.json per docs/STATE_SCHEMA.md."
    [ $a -gt 1 ] && prompt="$prompt RETRY $a of $attempts: first read state/$id.json and state/$id.verify.json (the independent verifier's failures) and the last 150 lines of logs/$id-attempt$((a-1)).log. Fix exactly those failures without redoing finished work. If the same error occurred twice, take the next fallback."
    log="logs/$id-attempt$a.log"; printf '%s' "$prompt" > "logs/$id-attempt$a.prompt.txt"
    if [ $FULL -eq 1 ]; then perm=(--dangerously-skip-permissions); else perm=(--permission-mode acceptEdits); fi
    say "start $id (attempt $a, timeout ${minutes}m)"
    timeout "${minutes}m" claude -p --model "$MODEL" --max-turns "$turns" --output-format text "${perm[@]}" < "logs/$id-attempt$a.prompt.txt" > "$log" 2>&1
    [ $? -eq 124 ] && say "TIMEOUT in $id after ${minutes}m"
    "$PY" scripts/verify_phase.py "$id" > "logs/$id-attempt$a.verify.log" 2>&1; ver=$?
    st=$(status "$id")
    if { [ "$st" = PASS ] || [ "$st" = DEGRADED ]; } && [ $ver -ne 0 ]; then setfail "$id" "agent reported $st but verify_phase failed"; st=FAIL; fi
    say "end $id (attempt $a): status=$st verified=$([ $ver -eq 0 ] && echo yes || echo no)"
    if [ "$st" = PASS ] || [ "$st" = DEGRADED ]; then done_=1; break; fi
    [ "$st" = STOP ] && { say "HARD STOP in $id. See STOPPED.md"; exit 2; }
    if tail -n 40 "$log" | grep -qiE "usage limit|rate limit|rate_limit|\b429\b|overloaded|limit reached" && [ $sleeps -lt $MAX_SLEEPS ]; then
      sleeps=$((sleeps+1)); a=$((a-1)); say "usage/rate limit; sleeping ${SLEEP_MIN}m ($sleeps/$MAX_SLEEPS)"; sleep $((SLEEP_MIN*60)); fi
  done
  if [ $done_ -eq 0 ]; then
    if [ "$critical" = 1 ]; then printf '# STOPPED in %s\nRead state/%s.verify.json and logs/%s-attempt*.log, fix the cause, then: ./run_autonomous.sh --start %s\n' "$id" "$id" "$id" "$i" > STOPPED.md; say "critical $id failed; stopping"; exit 3
    else say "non-critical $id failed; continuing"; fi
  fi
done
say "run complete. Read FINAL_REPORT.md"; for p in "${PHASES[@]}"; do echo "${p%%:*} $(status "${p%%:*}")"; done
