# Honcho Managed Memory Spike — MGS

Use when Rodolfo asks to evaluate or configure Honcho as a managed memory/conclusion layer for MGS agents.

## Operational framing

Honcho should not be treated as a canonical store for MGS facts. Treat it as a reasoning layer over sanitized history that can produce hypotheses/conclusions. Zeus must validate any operational conclusion against canonical sources before reporting or acting.

```text
Layer                         Canonical home
----------------------------  -----------------------------------------
Facts / permissions           JSON, DB, Git, WordPress, audit log
Procedures                    Hermes skills
Stable preferences            Hermes memory
Raw history                   Logs, Discord/session_search, events JSONL
Conclusions over history      Honcho-like reasoning layer
```

Recommended architecture:

```text
Sanitized MGS events/history  -> Honcho -> hypotheses / insights
Canonical MGS sources         -> Zeus   -> validation / final answer
```

## Managed API spike workflow

1. Do not send real MGS secrets, credentials, application passwords, raw private logs, or unsanitized user data to managed Honcho.
2. Create an isolated sandbox under `/root/mgs-agent/experiments/honcho-spike` or equivalent.
3. Use `uv` and the Python SDK:

```bash
uv add honcho-ai
```

4. Store the API key in 1Password, not chat:

```text
Vault: MGS Conteúdo
Item: Honcho API - MGS
Field: api key
```

5. Runtime environment should use variables only:

```bash
export HONCHO_API_KEY='***'
export HONCHO_WORKSPACE=mgs-honcho-spike
uv run python honcho_smoke.py
```

6. Add `.env` and `.venv/` to the local experiment `.gitignore`; include `.env.example` only.
7. The first validation should ingest only synthetic or sanitized messages and ask for a short operational conclusion with uncertainty.

## Minimal smoke script shape

```python
import os, sys
from honcho import Honcho

workspace = os.getenv("HONCHO_WORKSPACE", "mgs-honcho-spike")
api_key = os.getenv("HONCHO_API_KEY")
if not api_key:
    print("BLOCKED: HONCHO_API_KEY not set")
    sys.exit(2)

honcho = Honcho(workspace_id=workspace, api_key=api_key, environment="production")
rodolfo = honcho.peer("rodolfo-synthetic")
zeus = honcho.peer("zeus-synthetic")
atena = honcho.peer("atena-synthetic")

session = honcho.session("synthetic-agent-ops-001")
session.add_messages([
    rodolfo.message("Raquel asked for two synthetic RECs today and one image lookup failed."),
    atena.message("Synthetic REC Alpha failed image lookup; Synthetic REC Beta published as draft."),
    zeus.message("Preliminary synthetic conclusion: investigate image fallback before scaling."),
])

print(zeus.chat(
    "What operational conclusion would you draw about Atena? Keep it short and state uncertainty.",
    target=atena,
))
```

## Self-host decision point

Self-host is safer for real operational memory, but requires Docker/Postgres+pgvector/Redis and LLM provider configuration. Treat Docker/service installation on the VPS as a separate infrastructure action requiring normal MGS confirmation and validation.

## Pitfalls

- Do not let Honcho become source of truth for authorization, publication state, credentials, or incident status.
- Do not paste API keys into Discord. Report only item/field and presence/length if needed.
- Do not evaluate quality on a single happy-path answer. Compare against `session_search`/logs on a real question using sanitized excerpts.
- If using managed Honcho, default to synthetic/sanitized event summaries, not raw Discord transcripts.
