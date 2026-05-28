# Agent profile parity audit — applying Zeus/Atena standards to new agents

Use when Rodolfo asks to apply an existing Zeus/Atena standard to Ares or another new MGS agent, or asks to "varrer o sistema" for patterns that were not propagated.

## What to compare

Check both active profile files and repo-synced copies:

- `/root/.hermes/profiles/{agent}/SOUL.md`
- `/root/mgs-agent/profiles/{agent}-soul.md`
- `/root/.hermes/profiles/{agent}/config.yaml`
- `/root/mgs-agent/profiles/{agent}-config.yaml`
- `/root/mgs-agent/scripts/sync-souls.sh`
- `/root/mgs-agent/data/authorized-users.json`
- `/etc/systemd/system/{agent}-gateway.service`

## Standards commonly missed on new agents

```text
Pattern                         | Expected
--------------------------------|--------------------------------------------------
Response layout                 | Structured data uses aligned ```text``` tables
Markdown table pitfall          | Avoid raw `|---|---|` tables in Discord output
Executive short mode            | No filler open/close; concise, direct, opinionated
Credential handling             | Never print secrets; report item/field/status/len only
Validation before success       | Verify with real file/API/service/log evidence
REPORT-INFRA guidance           | Persistent infra changes must be reported to Zeus
Operational source list         | Agent knows where to inspect data/logs/git/APIs
Discord thread behavior         | auto-thread, descriptive rename, freeze existing thread
Thread membership               | `thread_auto_add_users` matches channel policy
Provider/model policy           | GPT-5.5 via openai-codex unless Rodolfo authorizes otherwise
Authorization registry          | Agent exists in authorized-users.json with Rodolfo whitelist
Versioning sync                 | SOUL/config and MGS-specific skills sync to repo
Systemd lifecycle               | gateway service active + enabled
```

## Response-layout rule to embed in SOUL

When the user says they prefer messages separated by `|---|---|` "porém em tabela", the intended implementation is not a Discord Markdown table. It is the MGS visual table pattern:

```text
[Título curto]

Campo do contexto     | Campo do contexto     | Campo do contexto
----------------------|-----------------------|------------------
valor real            | valor real            | valor real
valor real            | valor real            | valor real
```

Add this to the agent SOUL under communication/style, with context-specific column names and a rule not to force tables for one-sentence answers.

## Ares-specific note from 2026-05-27

Ares already had core config parity: GPT-5.5 Codex, `busy_input_mode: queue`, auto-thread, descriptive rename prompt, Rodolfo auto-add, smart approvals, authorized-users entry, active/enabled systemd service.

The gap found was content/style/ops parity in `SOUL.md` plus versioning coverage for MGS-specific Ares skills. The SOUL patch should include:

- MGS aligned `text` table rule, explicitly avoiding raw `|---|---|` Markdown tables for Discord readability.
- Executive short mode.
- Credential/no-secret rule with 1Password reporting only item/status/len.
- Validation-before-success rule.
- REPORT-INFRA guidance.
- Operational sources.

Remaining recommended infra follow-up: add sync coverage for `/root/.hermes/profiles/ares/skills/growth/` into `/root/mgs-agent/profiles/ares-skills/growth/`, especially `paid-acquisition-operations`, if Rodolfo authorizes modifying `sync-souls.sh`.

## Safety

Do not modify another profile's skills/config/SOUL unless Rodolfo explicitly asked to apply standards there. If the request is to audit only, report gaps and wait before touching infra sync/systemd/cron. SOUL/style edits requested directly by Rodolfo can be applied and then validated by checking active and repo copy match.
