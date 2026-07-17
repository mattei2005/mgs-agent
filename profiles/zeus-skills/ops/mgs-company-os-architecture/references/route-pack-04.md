### 7. Inventory deliverable format

After the blueprint, generate a migration inventory, usually under:

```text
/root/mgs-agent/docs/mgs-structure-inventory.md
```

Preferred columns:

```text
Path | Classe | Dono | Área | Status | Ação recomendada
```

Allowed actions:

```text
manter
não tocar
mover
renomear
consolidar
arquivar
remover depois
revisar com Rodolfo
```

Use `não tocar` for sensitive live state such as `data/sites.json`, `data/authorized-users.json`, active runners, active crons, and Hermes patches unless there is a specific approved plan.

Phase 3 inventory is a **risk map**, not a line-by-line content review. If Rodolfo asks what he has to review or says he does not understand the technical classification, reduce the approval question to the operating assumptions: `context/` is canonical/conceptual, `data/` is runtime, `scripts/` are productive automations, `profiles/` controls agent behavior one agent at a time, and Phase 4 should start with old `context/*.md` files before runtime/data/scripts. Give a clear COO recommendation instead of asking him to inspect every path.

When writing the inventory, include the current structural classes explicitly: `context/`, `profiles/`, `data/`, `scripts/`, `docs/`, `skills/`, `patches/`, `api/`, `tools/`, `backups/`, `experiments/`, `logs/`, and sensitive root files such as `.env`/auth/credentials. See `references/company-os-phase3-inventory-phase4-company-2026-06-07.md` for the v0.2 inventory/review pattern.

### 8. Executive communication pattern

When asking Rodolfo to review a document, do not make him infer what matters from the raw file. Default to the SOUL-style review format:

```text
1. O que faz sentido.
2. O que está demais / arriscado.
3. O que falta.
4. Pontos para Rodolfo classificar/corrigir.
```

Do **not** paste long files into chat for review. If Rodolfo asks to “show the file” or wants to read it like the screenshot example, send the current file as a native attachment (`MEDIA:/tmp/<review-file>.md`) so he can click/open it. Only paste the full file inline if he explicitly asks for inline content.

Discord formatting preference: avoid wide Markdown pipe tables when cells contain long prose. They render poorly on Discord/mobile and look like raw technical documents. Prefer either fenced `text` blocks with aligned short columns, or sectioned bullet blocks such as `O que faz sentido`, `O que está demais / arriscado`, `O que falta`, and `Minha recomendação`. Use Markdown tables only for compact labels/values that will not wrap badly.

Always separate:

```text
1. What changed / current file status.
2. The 5–10 operational decisions he actually needs to validate.
3. An attached file copy when he wants to inspect the whole artifact.
```

If Rodolfo says the review is confusing, switch from file content to decision-level validation: “you only need to confirm whether these statements are true.”

```text
Arquivo: path/to/file.md

O que faz sentido
-----------------
- keep / correct operational points

O que está demais / arriscado
-----------------------------
- overlong, redundant, risky, or wrong points

O que falta
-----------
- missing concepts / rules / operational details

Pontos para Rodolfo classificar/corrigir
----------------------------------------
1. concrete decisions for Rodolfo
```

If Rodolfo asks to “show the file” or wants to read it whole, **do not paste the entire markdown into chat**. Create/send it as a native attachment (`MEDIA:/tmp/...md`) so he can click and open the full file, matching the Discord preview/card style he prefers. Use a concise note plus the attachment. Inline full-file dumps are hard to read and should be avoided unless he explicitly asks to paste content.

If Rodolfo says the review is confusing, switch from raw file content to decision-level validation: “you only need to confirm whether these statements are true.”

If Rodolfo asks to review the raw file, **send it as a `MEDIA:/absolute/path` attachment** instead of pasting long markdown into Discord. He explicitly prefers attachments for SOUL/context/skill review files; paste only short excerpts or decision tables in chat.

Good pattern:

```text
Decisão                         Confirmação
------------------------------- ------------------------------------------------
Ares                            Campanhas only; no ChatPion/quiz/SMS.
agente legado                            Criativos + Drive.
Google Drive                    Source of approved creatives; agente legado/Ares R/W.
```

Avoid overexplaining. Give an operational opinion and the next concrete step.

## Pitfalls

- **Losing long-thread context**: in Company OS/restructuring threads, treat the thread as a persistent workstream until Rodolfo explicitly finalizes or changes objective. A short reply like “Ok”, “continue”, or “próximo” inherits the quoted/previous block context (phase, block, file) and must not be treated as a new standalone topic.
- **Renaming an active restructuring thread**: do not auto-rename an already-open Company OS thread while the objective is still the same. Never rename based on a short reply or quoted status. Thread title changes only make sense before/at creation or after a clear new objective with strong context. If a rename is genuinely required, preserve the workstream language; do not translate a PT-BR Company OS title into Spanish/English.
- **Moving before mapping**: creates broken imports, stale references, and agent confusion.
- **Treating current structure as garbage**: many existing MGS files are production-critical and should be wrapped, not replaced.
- **Letting agent prompts be the architecture**: prompts should consume the company OS, not be the only source of it.
- **Mixing concept and runtime**: `context/` is not `data/`; `docs/` is not `scripts/`.
- **Deleting backups/experiments too early**: classify first, archive later, delete only after explicit approval.
- **Updating agents too early**: validate blueprint with Rodolfo before changing Zeus/Atena/Ares behavior.
- **Skipping derived-doc approval**: after creating `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, and `permissions-matrix.md`, review/approve them one by one with Rodolfo before Phase 3 inventory. Do not treat the older canonical/runtime files listed inside `sources-of-truth.md` as Phase 2 manual-review targets; they belong in Phase 3 classification.
- **Over-assigning Ares**: Ares owns campaigns, not every acquisition-adjacent system. ChatPion/DigitalTrChat is configured by Rodolfo/Geizian/gestores; quiz/SMS/SMS Funnel setup is Rodolfo.
- **Duplicating source-of-truth rules everywhere**: detailed `Regra de conflito` sections belong mainly in `context/sources-of-truth.md`. Domain files like `sites.md`, `team.md`, `acquisition.md`, etc. may have a short note about their role, but avoid repeating full conflict matrices unless the file specifically governs source priority. Redundant rules make review harder and create drift.

