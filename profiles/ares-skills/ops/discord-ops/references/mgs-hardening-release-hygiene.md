# MGS hardening release hygiene

Use after a multi-step `/root/mgs-agent` hardening/audit run has already applied and validated fixes. This is not the primary audit checklist; it is the closing pass that turns a fragmented operational session into durable, searchable documentation.

## When to run

- Rodolfo says “continue” after the critical hardening blocks are complete.
- The repo has many auto-commits from `mgs-autocommit` and the final state is clean, but the story is hard to reconstruct from `git log` alone.
- A policy changed during the session (for example, Anthropic/Claude pay-per-token decommission) and runtime/docs need a clear current-state record.
- You need to distinguish active runtime risk from historical/documentation references before removing anything.

## Steps

1. **Scan references, classify instead of bulk deleting**
   - Search for policy-sensitive terms such as `Anthropic`, `Claude`, `provider: anthropic`, `StrictHostKeyChecking=no`, tempfiles, backup paths, or deprecated scripts.
   - Classify each hit as one of:
     - active runtime path;
     - fail-closed stub;
     - operational docs/skills;
     - historical changelog/archive;
     - untracked local backup.
   - Patch active runtime and misleading operational docs. Do not delete historical records just because they mention an old state.

2. **Write one release note under `docs/changelog/`**
   - Name it by date and class of work, e.g. `docs/changelog/YYYY-MM-DD_mgs-agent-hardening.md`.
   - Include:
     - objective and scope;
     - executive result table;
     - corrections by subsystem;
     - validations actually run;
     - service states;
     - commit anchors;
     - current policy decisions;
     - optional/non-critical next steps.
   - Do not include secrets, token values, webhook URLs, application passwords, or connection strings. Mention credential source only by item name/length when needed.

3. **Treat fragmented auto-commits as audit evidence, not a reason to rewrite history**
   - Record the important commit anchors in the release note.
   - If tempfiles or runtime files were committed and later removed, document that the HEAD state is clean.
   - Do not rewrite Git history unless Rodolfo explicitly authorizes it; force-push/history cleanup is destructive.

4. **Validate before reporting**
   - Check the release note exists and contains the policy/validation/commit sections.
   - Run `git diff --check` before committing docs.
   - Confirm `git status -sb` is clean/synced after commit/push or auto-push.
   - Confirm affected services remain in the expected state (`zeus-gateway`, `mgs-autocommit`, disabled legacy services).
   - Run a basic secret-literal check on the new release note before final report.

## Report format to Rodolfo

Use a compact aligned table:

```text
Entrega                         | Status
--------------------------------|---------------------------------------------
Release note consolidada        | Criada em docs/changelog/...
Referências sensíveis           | Classificadas: runtime/docs/histórico
Runtime legado                  | fail-closed / masked / inactive
Git                             | limpo / main...origin/main
Serviços                        | zeus active, autocommit active, ...
```

End with `Próximo passo pendente:` and name the next concrete safe block, or state that only optional/non-critical work remains.

## Pitfalls

- Do not “sanitize” history by deleting legitimate historical changelogs; update misleading operational instructions instead.
- Do not expose raw credential values while validating 1Password/GitHub access.
- Do not squash/rewrite auto-commit history as a cleanup step without explicit authorization.
- Do not claim the repo is synced until `git status -sb` verifies it after the documentation commit.
