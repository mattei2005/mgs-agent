# REC+P1 universal contract patch application — 2026-05-29

## Context

Rodolfo supplied a ZIP handoff for a REC+P1 refactor that replaces per-`template_key` REC templates and GB-only P1 gating with universal contracts:

- `contracts/cc-rec.md`
- `contracts/cc-p1.md`
- optional `--lang` override for REC, P1 and the orchestrator

The ZIP used dev repo filenames at the root (`rec.py`, `p1.py`, `orch.py`), while production `mgs-agent` uses scripts under `/root/mgs-agent/scripts/`.

## Durable workflow

When applying external REC/P1 runner patches:

1. Inspect ZIP contents read-only and compile the staged Python files before touching production files.
2. Map dev filenames to production paths explicitly:
   - `rec.py` -> `scripts/mgs-rec-runner.py`
   - `p1.py` -> `scripts/mgs-p1-runner.py`
   - `orch.py` -> `scripts/mgs-rec-p1-orchestrator.py`
   - `skills/content-generate-rec/contracts/*.md` -> same contracts path in repo
3. If the repo working tree is dirty, do not block automatically, but state that unrelated files exist and only modify the patch targets.
4. Keep legacy `templates/rec-*.md` on disk unless Rodolfo explicitly asks to delete/archive them; they are rollback material even if the new runner stops loading them.
5. Back up overwritten production files to `/tmp/.../backups/<timestamp>/` before replacement.
6. Validate in this order:
   - `python3 -m py_compile scripts/mgs-rec-runner.py scripts/mgs-p1-runner.py scripts/mgs-rec-p1-orchestrator.py`
   - dry-run through the orchestrator with a real site key from `data/sites.json`, not a template key unless the repo actually uses template keys as site keys
   - inspect reported `policy.contract_rec` and `policy.contract_p1`
   - verify `--lang` is propagated to REC and P1 runners
   - verify P1 no longer gates on `template_key == 'gb-cc-en'`
   - verify the P1 runner actually reads/uses `contracts/cc-p1.md`, not only that the orchestrator reports it
7. If Rodolfo instructs “if a dry-run breaks, don’t fix,” stop after the first failing dry-run and report the full JSON/traceback plus paths attempted.

## Pitfall found

A patch can pass `py_compile` and the orchestrator can report `contract_p1`, while `mgs-p1-runner.py` itself only removes the old gate and adds `--lang` but does not explicitly read `contracts/cc-p1.md`. Treat this as a validation finding, not as success.

## Reporting notes

Final report should separate:

- files applied
- py_compile output
- each dry-run command/output actually executed
- dry-runs skipped because the first one failed
- `git status --short` after application
- unrelated dirty working-tree entries vs. patch-owned entries
