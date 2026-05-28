# GPT-5.5/OpenAI-Codex all-profiles purge pattern

Use when Rodolfo says variants of: “GPT-5.5 pra tudo”, “zero Anthropic”, “deleta de tudo”, or asks to remove Claude/Anthropic from active MGS agents.

## Scope

Profiles currently in scope: `zeus`, `atena`, `ares`.

Targets to inspect and clean without printing secrets:

- `/root/.hermes/auth.json`
- `/root/.hermes/profiles/{zeus,atena,ares}/auth.json`
- `/root/.hermes/.env`
- `/root/mgs-agent/.env`
- `/root/.hermes/profiles/{zeus,atena,ares}/.env`
- `/root/.hermes/state-snapshots/**/{auth.json,.env}`
- `/root/.hermes/backups/**`
- `/root/mgs-agent/backups/**`
- `/root/mgs-agent/data/config-backups/**`
- mirrored configs in `/root/mgs-agent/profiles/{agent}-config.yaml`

## Procedure

1. Treat deletion of credentials/tokens as Critical Subset: confirm explicitly before mutating.
2. Pin each profile config:
   - `model.provider: openai-codex`
   - `model.default: gpt-5.5`
   - `model.base_url: https://chatgpt.com/backend-api/codex`
   - every `auxiliary.*.provider: openai-codex`
   - every `auxiliary.*.model: gpt-5.5`
3. In every auth JSON, remove both:
   - `providers.anthropic`
   - `credential_pool.anthropic`
   - set `active_provider=openai-codex` if needed.
4. In `.env` files, remove any key whose name contains `ANTHROPIC` or `CLAUDE`.
5. Delete local backup/snapshot files that contain actual Anthropic credential material (`sk-ant-*`, `ANTHROPIC_API_KEY`, or `credential_pool` with `anthropic`).
6. Redact actual key strings in logs/session dumps if deleting the entire file would destroy useful audit history.
7. Do **not** delete or patch upstream Hermes source/tests/docs just because they contain strings like `anthropic_adapter.py`, `claude-*`, or example `sk-ant-*`. Those are framework capabilities/tests, not active MGS credentials.
8. Do not byte-rewrite arbitrary binaries. If a broad redaction pass touched executable files, verify magic/version after (`tirith --version`, ELF magic if available). Prefer text-only redaction for future runs.
9. Copy live configs into `/root/mgs-agent/profiles/{agent}-config.yaml` directly after mutation; `sync-souls.sh` only copies configs when source mtime is newer than target, so a fast/mtime edge can leave mirrors stale.
10. Restart gateways carefully:
    - Restart Atena/Ares normally and wait through drain timeouts.
    - Zeus restart may interrupt the current response; schedule delayed/background restart only if the user explicitly requested full activation before replying.

## Validation

Report only counts/booleans, never token values:

- For each profile: main model/provider and every auxiliary provider/model is `openai-codex/gpt-5.5`.
- Root auth + profile auths: `providers.anthropic=false`, `credential_pool.anthropic=false`, `active_provider=openai-codex`.
- Credential scan outside upstream source/tests/docs/examples: actual-looking `sk-ant-*` count is `0`.
- Gateways active and Discord connected for Atena/Ares; Zeus restart status if scheduled.
- Commit hash if mirrored configs/backups in `/root/mgs-agent` changed.

## Pitfalls from 2026-05-26

- Initial scan that only checked top-level `auth.json` providers missed `credential_pool.anthropic`. Always inspect both structures.
- Root `~/.hermes/.env` and root `~/.hermes/auth.json` can retain credentials even when profile files are clean.
- State snapshots/backups commonly retain old auth/env secrets; include them in the purge.
- `sync-souls.sh` mtime check may not mirror freshly rewritten configs; explicit copy is safer after a forced policy change.
- `systemctl restart atena-gateway` can remain `deactivating/stop-sigterm` while draining an active turn for ~240s. Wait and then re-check before declaring failure.
