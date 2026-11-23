# Environment (no secrets)

- OS: Windows 11 (Git Bash for the Bash tool; PowerShell harness)
- Venv python: `.venv/Scripts/python` (Python 3.13.14)
- Node: v22.17.0; git: 2.50.0.windows.1; synapse-cli: 0.1.9
- git core.autocrlf=false (keeps generated-server hash fingerprints stable)
- Models (state/models.json, paid endpoints, ARENA_ALLOW_FREE=0): arena/attacker/synapse = nvidia/nemotron-3.5-super-vl; sweep = nvidia/nemotron-3.5-lightning. ping_model.py: all three returned tool_calls=1.
- SYNAPSE_MODEL_FALLBACKS (validated tool-capable on OpenRouter): deepseek/deepseek-v4.1-flash-1017, openai/gpt-6-luna
- Synapse model choice for phase 01: `synapse build --local --provider openrouter --model <id>` (build has a --model flag, so no `synapse model set` needed)

## synapse build --help / synapse model --help
```
Usage: synapse build [options]

Build MCP server based on requirements

Options:
  -q, --query <query>    v2 custom: workflow intent
  --auto                 v2: force Auto track (expose HTTP endpoints via
                         runner)
  --custom               v2: force Custom track (compose internal functions)
  --base-url <url>       v2 auto: deployed base URL for the API
  --server-name <name>   v2 auto: MCP server name (default: folder name).
                         Rebuilds update the server with this name; a different
                         name gives the repo a second server
  --new                  v2 auto: create a new MCP server instead of updating
                         this repo's existing one (new server id)
  --all-endpoints        v2 auto: expose every detected endpoint without the
                         picker (implies --auto; for CI / no TTY)
  --endpoints <list>     v2 auto: comma-separated endpoints to expose without
                         the picker — "GET /path", "/path" or tool names
                         (implies --auto; for CI / no TTY)
  --smart-names          v2 auto: read handler source (+ README/docs) to
                         name/describe tools from real behavior instead of
                         route + docstring alone. Local runs it on your
                         configured provider; hosted runs it server-side.
  --resume               v2: resume the most recent unfinished discover session
                         for this repo
  --discover             v2: rescan the code instead of reusing the endpoints
                         found by the last build
  --max-time <minutes>   v2: soft wall-clock cap in minutes (default 15)
  --deep                 v2 custom: raise candidate cap from 200 to 500 during
                         classification
  --local                One-shot override: run this build locally on your own
                         model. Uses the provider from `synapse model`. Doesn't
                         change the project's stored mode.
  --provider <name>      --local: provider for this build — anthropic | openai
                         | groq | grok | openrouter | ollama | custom | bedrock
                         | vertex
  --model <id>           --local: model id for this build (pins every stage)
  --llm-base-url <url>   --local: OpenAI-compatible endpoint for this build
  --llm-api-key <key>    --local: inference API key for this build
  --llm-region <region>  --local: AWS region (bedrock) or Vertex location for
                         this build
  --llm-project <id>     --local: GCP project for vertex for this build
  --anthropic-key <key>  Deprecated alias for --llm-api-key; implies --provider
                         anthropic.
  -h, --help             display help for command
---
Usage: synapse model [options] [command]

Show or switch the inference provider used by local builds (`synapse build
--local`)

Options:
  -h, --help                display help for command

Commands:
  list                      List supported inference providers and their
                            default models
  set [options] <provider>  Switch provider: anthropic | openai | groq | grok |
                            openrouter | ollama | custom | bedrock | vertex
  reset [options]           Remove the saved inference config (local builds
                            return to Anthropic)
```
