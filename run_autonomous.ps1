<#
Lakshman Rekha: unattended build driver (Windows PowerShell 5.1+ / 7).
Each phase = one fresh headless Claude Code session (prompt via stdin), with a wall-clock timeout.
After each phase the driver INDEPENDENTLY runs scripts/verify_phase.py; the agent's own status is not trusted.

  .\run_autonomous.ps1                 # safe mode: allowlist in .claude/settings.json (unlisted commands auto-denied, no stalls)
  .\run_autonomous.ps1 -FullAuto       # bypass permissions (the guard hook + verify_phase still apply); dedicated folder only
  .\run_autonomous.ps1 -StartPhase 3   # resume
  .\run_autonomous.ps1 -DryRun         # print the plan, run nothing
#>
param(
  [string]$Model = $(if ($env:REKHA_CLAUDE_MODEL) { $env:REKHA_CLAUDE_MODEL } else { "claude-opus-5-5" }),
  [int]$StartPhase = 0,
  [switch]$FullAuto,
  [switch]$Force,
  [switch]$DryRun,
  [int]$LimitSleepMinutes = 20,
  [int]$MaxLimitSleeps = 9
)
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

# id, critical, max attempts, max turns, timeout minutes
$phases = @(
  @{ id = "00-preflight";       critical = $true;  attempts = 3; turns = 80;  minutes = 45  },
  @{ id = "01-compose";         critical = $true;  attempts = 3; turns = 200; minutes = 120 },
  @{ id = "02-baseline-runner"; critical = $true;  attempts = 3; turns = 300; minutes = 180 },
  @{ id = "03-viewer";          critical = $false; attempts = 2; turns = 200; minutes = 90  },
  @{ id = "04-arena";           critical = $true;  attempts = 3; turns = 250; minutes = 360 },
  @{ id = "05-distinctive";     critical = $false; attempts = 2; turns = 300; minutes = 240 },
  @{ id = "06-submission";      critical = $false; attempts = 2; turns = 300; minutes = 180 }
)

New-Item -ItemType Directory -Force -Path state, logs | Out-Null
$py = if (Test-Path ".venv/Scripts/python.exe") { ".venv/Scripts/python.exe" } else { "python" }

function Say([string]$m) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [driver] $m"
  Write-Host $line
  Add-Content -Path PROGRESS.md -Value "- $line" -Encoding utf8
}
function Get-Status([string]$id) {
  $f = "state/$id.json"
  if (-not (Test-Path $f)) { return "MISSING" }
  try { return (Get-Content $f -Raw | ConvertFrom-Json).status } catch { return "UNREADABLE" }
}
function Set-Status([string]$id, [string]$status, [string]$why) {
  $f = "state/$id.json"
  $o = if (Test-Path $f) { try { Get-Content $f -Raw | ConvertFrom-Json } catch { $null } } else { $null }
  if (-not $o) { $o = [pscustomobject]@{ phase = $id } }
  $o | Add-Member -NotePropertyName status -NotePropertyValue $status -Force
  $o | Add-Member -NotePropertyName driver_note -NotePropertyValue $why -Force
  [IO.File]::WriteAllText((Join-Path $PSScriptRoot $f), ($o | ConvertTo-Json -Depth 8))   # UTF-8, no BOM
}

# Application type = claude.exe or claude.cmd (Start-Process can't launch the claude.ps1 shim)
$claude = Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $claude) { Write-Error "Claude Code CLI 'claude' (exe/cmd) not found on PATH."; exit 1 }
if (-not (Test-Path .env)) { Write-Error ".env missing: copy .env.example to .env and fill in OPENROUTER_API_KEY and REKHA_TOKEN_SECRET."; exit 1 }
if (Test-Path STOPPED.md) { Remove-Item STOPPED.md }

if ($DryRun) {
  foreach ($p in $phases) { "{0,-20} critical={1} attempts={2} turns={3} timeout={4}m status={5}" -f $p.id, $p.critical, $p.attempts, $p.turns, $p.minutes, (Get-Status $p.id) | Write-Host }
  exit 0
}

$sleeps = 0; $started = Get-Date
Say "run started (model=$Model fullAuto=$FullAuto start=$StartPhase)"

for ($i = $StartPhase; $i -lt $phases.Count; $i++) {
  $p = $phases[$i]; $id = $p.id
  $st = Get-Status $id
  if (-not $Force -and ($st -eq "PASS" -or $st -eq "DEGRADED")) { Say "skip $id ($st)"; continue }

  $attempt = 0; $done = $false
  while (-not $done -and $attempt -lt $p.attempts) {
    $attempt++
    $prompt = "You are running UNATTENDED: no human will answer until the run ends. Read CLAUDE.md, then execute .claude/commands/$id.md exactly. Never ask questions; follow docs/FALLBACKS.md and log decisions in docs/DECISIONS.md. End by writing state/$id.json per docs/STATE_SCHEMA.md."
    if ($attempt -gt 1) {
      $prompt += " RETRY $attempt of $($p.attempts): first read state/$id.json and state/$id.verify.json (the independent verifier's failures) and the last 150 lines of logs/$id-attempt$($attempt - 1).log. Fix exactly those failures without redoing finished work. If the same error occurred twice, take the next fallback."
    }
    $promptFile = "logs/$id-attempt$attempt.prompt.txt"
    $log = "logs/$id-attempt$attempt.log"
    $err = "logs/$id-attempt$attempt.err.log"
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot $promptFile), $prompt)   # UTF-8, no BOM
    $cliArgs = @("-p", "--model", $Model, "--max-turns", "$($p.turns)", "--output-format", "text")
    if ($FullAuto) { $cliArgs += "--dangerously-skip-permissions" } else { $cliArgs += @("--permission-mode", "acceptEdits") }

    Say "start $id (attempt $attempt, timeout $($p.minutes)m)"
    $proc = Start-Process -FilePath $claude.Source -ArgumentList $cliArgs -NoNewWindow -PassThru `
            -RedirectStandardInput $promptFile -RedirectStandardOutput $log -RedirectStandardError $err
    if (-not $proc.WaitForExit($p.minutes * 60 * 1000)) {
      Say "TIMEOUT in $id after $($p.minutes)m; killing the process tree"
      & taskkill /PID $proc.Id /T /F | Out-Null
    }

    # independent verification, never trusting the agent's claim
    & $py scripts/verify_phase.py $id *> "logs/$id-attempt$attempt.verify.log"
    $verified = ($LASTEXITCODE -eq 0)
    $st = Get-Status $id
    if (($st -eq "PASS" -or $st -eq "DEGRADED") -and -not $verified) {
      Set-Status $id "FAIL" "agent reported $st but scripts/verify_phase.py failed (see state/$id.verify.json)"
      $st = "FAIL"
    }
    Say "end $id (attempt $attempt): status=$st verified=$verified"

    if ($st -eq "PASS" -or $st -eq "DEGRADED") { $done = $true; break }
    if ($st -eq "STOP") { Say "HARD STOP in $id. See STOPPED.md"; exit 2 }

    $tail = (Get-Content $log, $err -Tail 40 -ErrorAction SilentlyContinue) -join "`n"
    if ($tail -match "usage limit|rate limit|rate_limit|\b429\b|overloaded|limit reached" -and $sleeps -lt $MaxLimitSleeps) {
      $sleeps++; $attempt--
      Say "usage/rate limit detected; sleeping $LimitSleepMinutes min ($sleeps/$MaxLimitSleeps); attempt not counted"
      Start-Sleep -Seconds ($LimitSleepMinutes * 60)
    }
  }

  if (-not $done) {
    if ($p.critical) {
      @"
# STOPPED in $id
Failed $($p.attempts) attempts. Read: state/$id.verify.json, state/$id.json, logs/$id-attempt*.log
Fix the cause (keys/credit, a tool install, a Synapse model), then resume:
    .\run_autonomous.ps1 -StartPhase $i
"@ | Out-File -FilePath STOPPED.md -Encoding utf8
      Say "critical phase $id failed; stopping (STOPPED.md)"
      exit 3
    }
    Say "non-critical phase $id failed; continuing"
  }
}

$mins = [int]((Get-Date) - $started).TotalMinutes
Say "run complete in $mins min. Read FINAL_REPORT.md"
foreach ($p in $phases) { "{0,-20} {1}" -f $p.id, (Get-Status $p.id) | Write-Host }
