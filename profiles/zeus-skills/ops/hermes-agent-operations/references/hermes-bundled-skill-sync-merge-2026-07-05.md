# Hermes bundled skill sync merge — 2026-07-05

Use when `hermes update` reports `user-modified bundled skill(s) (kept as-is)` and Rodolfo asks Zeus to compare, merge, or decide what to do.

## Core rule

Do **not** blindly run `hermes skills reset <skill> --restore` on every modified bundled skill. Classify each diff first:

- **Empty/stale local copy** → restore stock (`--restore --yes`).
- **Local artifact only** (`__pycache__`, temporary files) → move artifact to a secure rollback directory (or delete only after any required critical confirmation), then rebaseline.
- **Useful local addition only** → keep local copy and rebaseline.
- **Both sides useful** → merge manually, then rebaseline the manifest to the merged copy.

## Safe workflow

1. **Inventory all profiles**

```bash
hermes skills list-modified
for p in zeus atena ares legacy-agent; do hermes -p "$p" skills list-modified; done
```

2. **Generate diffs before changing anything**

```bash
hermes skills diff <skill> > reports/.../root__<skill>.diff
hermes -p <profile> skills diff <skill> > reports/.../<profile>__<skill>.diff
```

3. **Backup skill roots**

Back up `/root/.hermes/skills` and `/root/.hermes/profiles/{zeus,atena,ares,legacy-agent}/skills` before any restore/merge.

4. **Apply by classification**

- Restore stock for stale/empty local copies.
- For artifact-only drift, preserve rollback by moving junk outside the skill tree before rebaseline; avoid irreversible deletion when the operation requires separate confirmation.
- For merges, start from the current bundled stock in `/root/.hermes/hermes-agent/skills/...`, then add back only useful local operational content.

5. **Rebaseline intentionally**

`hermes skills reset <skill>` records the current copy as accepted baseline for future update comparisons. If the CLI path is unavailable in the active gateway context, update `.bundled_manifest` with the same directory MD5 algorithm used by `tools/skills_sync.py::_dir_hash`: sorted files, relative path bytes, then file bytes.

6. **Validate**

```bash
hermes skills list-modified
for p in zeus atena ares legacy-agent; do hermes -p "$p" skills list-modified; done
```

Expected final state after a clean merge/rebaseline:

```text
No user-modified bundled skills — everything tracks upstream.
```

Also validate frontmatter for edited skills: starts at byte 0 with `---`, has `name` and `description`, and description length is ≤1024 chars.

## Session-specific result pattern

In the 2026-07-05 merge:

- `ocr-and-documents` root/Zeus/Ares/agente legado: restored stock because local copy was stale/empty.
- agente legado `google-workspace`: removed `scripts/__pycache__` artifact and rebaselined.
- `ascii-video` root/Zeus/agente legado: kept local static ASCII art addition and rebaselined.
- `hermes-agent-skill-authoring` root/Zeus: merged stock 1.1.0 with MGS rename/migration validation rule.
- Atena `hermes-agent`: merged stock 2.3.0 with local consolidated subsystem notes.
- agente legado `claude-design`: merged stock 1.1.0 with local absorbed subworkflows.
- agente legado `systematic-debugging`: merged stock 1.1.0 with local adjacent validation modes.

## Reporting standard

Report the classification and final validation, not the raw diffs. Include backup path and validation artifact path. No restart is required for skill-only changes; they take effect on future skill loads/sessions.
