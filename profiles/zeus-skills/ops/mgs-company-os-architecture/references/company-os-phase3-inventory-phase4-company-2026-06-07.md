# Company OS — Phase 3 Inventory and Phase 4 First Context Block (2026-06-07)

## Session lessons

Rodolfo approved the Company OS Phase 2 consistency audit and asked what he had to review in Phase 3. The useful framing was: Phase 3 is a **risk map**, not a line-by-line content review.

## Phase 3 review framing

When presenting a classified inventory to Rodolfo, do not ask him to understand every path. Ask him to validate the operating assumptions:

```text
1. context/ is the conceptual/canonical company layer.
2. data/ is runtime/operational state and must not be mass-edited.
3. scripts/ are productive automations and require dry-run/test/rollback.
4. profiles/ controls agent behavior and must change one agent at a time.
5. Phase 4 should start with old context/*.md files before data/scripts/runtime.
```

If Rodolfo says he does not understand the technical review, give the COO recommendation directly: approve the inventory as the initial risk map and proceed to the lowest-risk block.

## Inventory v0.2 pattern

The inventory should cover both high-level folders and special-case files/classes:

```text
context/      canonical company knowledge
profiles/     versioned SOUL/config/custom skills for agents
data/         runtime state, caches, DBs, operational JSON
scripts/      productive automations and monitors
docs/         plans, changelog, CRONS, inventories
skills/       shared operational skills
patches/      local Hermes/MGS runtime patches
api/          API/runtime support
tools/        auxiliary tools
backups/      backup/safety copies
experiments/  spikes and proofs of concept
logs/         audit/runtime logs
.env/auth     sensitive/non-versioned
```

Use explicit risk language: `manter`, `não tocar`, `revisar depois`, `arquivar depois`, `alterar só com plano`.

## Phase 4 first block pattern: context/company.md

When starting Phase 4 with `context/company.md`:

1. Read `context/company.md` plus `context/company-os.md` and `context/company-current-operating-model.md`.
2. Keep the edit conceptual and low-risk.
3. Do not rewrite the whole file if it is already mostly aligned.
4. Patch only drift/ambiguity, e.g. missing `Office / Follow-up`, ActiveView exception, agent-architecture rule, or gestor scope wording.
5. Validate stale terms and key assertions.
6. Run diff/secret checks, then rely on the repo auto-commit watcher if it commits; verify `HEAD == origin/main` before reporting.

## Communication pattern

For Phase 3/4 progress, report in executive form:

```text
Arquivo / fase
Status
Validação
Secret scan
Commit / auto-push
Repo limpo
Ajustes feitos
Próximo bloco recomendado
```

Do not ask Rodolfo to review low-level path details unless a classification decision has real business/risk tradeoff.