# MGS agent profile pattern rollout

Use this reference when Rodolfo asks to apply Zeus/Atena standards to a newer agent such as Ares, or asks to "varrer o sistema" for missing profile patterns.

## What to compare

Audit the new agent against Zeus/Atena in these areas:

```text
Área                  | Padrão esperado
----------------------|---------------------------------------------------------
SOUL.md style          | modo executivo curto, PT-BR, no filler, no generic close
Response layout        | aligned `text` block tables, not raw Markdown `|---|---|`
Credential safety      | no plain secrets; 1Password only internally; report item/len/status
Validation discipline  | validate state changes before reporting success
Operational sources    | consult /root/mgs-agent data/logs/git/APIs before claiming facts
REPORT-INFRA           | infra changes reported to Zeus when relevant
Discord behavior       | auto-thread, descriptive rename, freeze after create, auto-add users
Model/provider         | gpt-5.5 via openai-codex unless Rodolfo explicitly authorizes otherwise
Versioning             | SOUL/config and MGS-specific skills sync into /root/mgs-agent/profiles
Authorization          | agent present in data/authorized-users.json with Rodolfo whitelist
Systemd                | service exists, active, enabled when agent is live
```

## Layout rule to embed in SOUL.md

When the user complains about messages formatted as Markdown tables with raw separators like `|---|---|`, encode the preference in the agent SOUL.md:

- Use aligned tables inside `text` code blocks for structured/comparable data.
- Do not use raw Markdown table syntax when Discord rendering will be cramped or ugly.
- Column names must come from the current context, not copied from examples.
- Do not put mentions that must notify users inside code blocks.

## Sync/versioning rule for new agents

If a new agent has MGS-specific skills, do not leave them only under `/root/.hermes/profiles/<agent>/skills/`. Add the appropriate category to `/root/mgs-agent/scripts/sync-souls.sh`, run it once, and verify the synced files under `/root/mgs-agent/profiles/<agent>-skills/`.

Current known selective sync categories:

```text
Agent | MGS-specific skill categories
------|-------------------------------
Zeus  | ops/
Atena | wordpress/, devops/, autonomous-ai-agents/openhands only
Ares  | growth/
```

For Ares, the durable pattern is:

```bash
# Ares: growth/ (skills de aquisição paga, criativos e operações ads MGS)
mkdir -p "$TARGET_DIR/ares-skills"
if [ -d "$PROFILES_DIR/ares/skills/growth" ]; then
    rsync -a --delete \
        "$PROFILES_DIR/ares/skills/growth/" \
        "$TARGET_DIR/ares-skills/growth/" \
        && echo "$(date -Iseconds) synced ares skills/growth"
fi
```

Validation:

```bash
bash -n /root/mgs-agent/scripts/sync-souls.sh
/root/mgs-agent/scripts/sync-souls.sh
test -f /root/mgs-agent/profiles/ares-skills/growth/paid-acquisition-operations/SKILL.md
```

## AGENT.md policy update safety

Editing `/root/mgs-agent/AGENT.md` is in the Critical Subset and needs explicit double-confirmation. For adding Ares `growth/`, update:

- `Skills MGS-específicas (em sync para Git)` list: add `Ares: growth/`.
- `Categorias MGS-específicas que disparam REPORT-INFRA`: add `Ares: skills/growth/`.
- Inventory schema category examples: include `growth`.

Verify by reading the updated section and checking markers:

```text
**Ares:** `growth/`
**Ares:** `skills/growth/`
<ops|wordpress|devops|growth>
```

## Reporting shape

Report concise, evidence-first:

```text
Área           | Resultado | Evidência
---------------|-----------|-----------------------------------------------
SOUL ativo     | Corrigido | /root/.hermes/profiles/ares/SOUL.md
Cópia Git      | Corrigido | /root/mgs-agent/profiles/ares-soul.md
Sync skills    | OK        | profiles/ares-skills/growth/... criado
AGENT.md       | OK        | Ares growth oficializado
Restart        | Não       | docs/sync apenas
```
