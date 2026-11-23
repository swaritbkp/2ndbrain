# Claude Desktop config (F11): composed tools (Route B, two servers)
Add to `%APPDATA%\Claude\claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`). Adjust paths.
```json
{
  "mcpServers": {
    "rekha-preview": {
      "command": "C:/2ndbrain/.venv/Scripts/python.exe",
      "args": ["C:/2ndbrain/preview_rebalance_switch_server.py"],
      "cwd": "C:/2ndbrain",
      "env": {"PYTHONPATH": "C:/2ndbrain;C:/2ndbrain/src", "REKHA_DB": "C:/2ndbrain/data/rekha.db",
              "REKHA_NOW": "2026-11-23T14:55:00+05:30", "REKHA_AS_OF": "2026-11-23", "REKHA_TOKEN_SECRET": "<same secret as your env>"}
    },
    "rekha-confirm": {
      "command": "C:/2ndbrain/.venv/Scripts/python.exe",
      "args": ["C:/2ndbrain/confirm_rebalance_switch_server.py"],
      "cwd": "C:/2ndbrain",
      "env": {"PYTHONPATH": "C:/2ndbrain;C:/2ndbrain/src", "REKHA_DB": "C:/2ndbrain/data/rekha.db",
              "REKHA_NOW": "2026-11-23T14:55:00+05:30", "REKHA_AS_OF": "2026-11-23", "REKHA_TOKEN_SECRET": "<same secret as your env>"}
    }
  }
}
```
The 6-digit code appears only in the `oob_outbox` table (the RM console), never in tool output. *Fictional data. Indicative estimate only. Not tax or investment advice.*
