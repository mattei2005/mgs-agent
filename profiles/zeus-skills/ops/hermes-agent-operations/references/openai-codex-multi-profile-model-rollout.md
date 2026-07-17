# OpenAI-Codex multi-profile model rollout

Use this playbook when changing the principal OpenAI-Codex model or reasoning level across Zeus/Atena/Ares/agente legado.

## Core distinctions

- `model.default` controls the principal agent model.
- `agent.reasoning_effort` is a **static profile default**. Valid gateway values include `medium`, `high`, and `xhigh` (Extra High).
- `display.show_reasoning` only controls whether reasoning is shown; it does not change reasoning effort.
- `auxiliary.*.model` controls separate tasks such as vision, web extraction, compression, titles, approvals and MCP. Changing only `model.default` does not migrate those tasks.
- Do not claim task-based automatic routing unless a live gateway code path actually classifies each incoming turn and sets the per-turn reasoning config. A fixed `high` default is not automatic routing.
- Sol Pro is a distinct model entitlement/slug. If live Codex discovery does not expose a Pro slug, do not configure or promise it. `xhigh` on normal Sol is not Pro.

## Preflight

1. Fetch the live Codex model catalog using an existing OAuth session without printing token material.
2. Confirm the requested slug is present in the live catalog.
3. For every target profile, inspect sanitized auth state:
   - intended provider;
   - access token present;
   - refresh token present;
   - no unresolved `last_auth_error` when available.
4. Inventory both the live config and versioned mirror:
   - `/root/.hermes/profiles/<agent>/config.yaml`
   - `/root/mgs-agent/profiles/<agent>-config.yaml`
5. Decide and state scope explicitly: principal only, auxiliaries too, static reasoning default, and whether dynamic routing is genuinely being implemented.

## Credential repair gate

Copying or replacing any production OAuth/token block is in the MGS Critical Subset and requires double confirmation even when the overall rollout was requested.

After confirmation:

1. Back up the affected `auth.json` outside Git under `/root/.hermes/secure-backups/<agent>/`, mode `600`.
2. Copy only the known-good `providers.openai-codex` block from a profile that passed a real smoke call.
3. Preserve/restore the target profile's intended `active_provider`.
4. Never print tokens or place auth backups under `/root/mgs-agent`.
5. Run a real smoke call for the repaired profile before continuing.

## Rollout

1. Update live configs and mirrors together.
2. Set `model.default` and `agent.reasoning_effort` to the approved values.
3. Update auxiliaries only when included in the approved scope; keep lightweight auxiliaries on an older model only if that was an explicit decision.
4. Validate YAML/config schema and exact live↔mirror equality.
5. Run one real smoke call per profile. Config readback alone is insufficient.
6. Restart gateways with the detached MGS safe-restart flow; Zeus last.
7. After restart, verify all services `active/running` and repeat per-profile smoke calls or obtain logs proving the intended model handled a real turn.
8. Record audit log, refresh infra inventory, and send REPORT-INFRA through the infra channel.

## Completion gate

Do not say “ready”, “done”, or “all migrated” unless all of these are true:

- requested model appears in live discovery;
- every target live config and mirror matches;
- every target profile has functional auth;
- every target profile passes a real inference smoke;
- all restarted gateways are active;
- automatic routing claims are backed by actual per-turn implementation/tests;
- Pro availability is reported exactly as exposed by the provider;
- principal-versus-auxiliary scope is explicit;
- audit, inventory and REPORT-INFRA are complete.

If one profile fails auth or only configuration was validated, report the rollout as partial and identify the blocker. A successful smoke on one agent does not validate the others.
