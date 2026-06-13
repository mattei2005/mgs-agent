# Atena SOUL + Phase 2 cleanup sequencing (2026-06-13)

## Context

During Atena reconstruction, Rodolfo approved a compact SOUL that keeps identity/governance in SOUL and operational REC+P1 procedure in SKILL/contracts/runners. The live runtime SOUL is `/root/.hermes/profiles/atena/SOUL.md`; the versioned mirror is `/root/mgs-agent/profiles/atena-soul.md`. Keep both identical when applying SOUL changes.

## Authorization wording settled by Rodolfo

For Atena content/article requests:

- Rodolfo or Raquel can request articles directly.
- If anyone else requests an article, Atena should ask Rodolfo instead of executing automatically.
- The authorization choices are simple: `uma vez só`, `somente nesta sessão/thread`, or `sempre autorizada`.
- Avoid importing Zeus's broader `one-time/limited/full` matrix wording into Atena SOUL for this article-request flow unless Rodolfo explicitly changes the design.

## Application pattern used successfully

1. Build the corrected SOUL from the current source, not stale local copies.
2. Backup both live and versioned SOUL files.
3. Write the same content to:
   - `/root/.hermes/profiles/atena/SOUL.md`
   - `/root/mgs-agent/profiles/atena-soul.md`
4. Validate `sha256`, `cmp`, `grep -c "REGRA [0-9]" == 0`, and absence of old authorization terms.
5. Restart `atena-gateway.service` and check recent journal for `Traceback|ERROR|CRITICAL|Exception`.
6. Append an event to `/root/mgs-agent/logs/events-audit.jsonl`.
7. Let auto-push sync Git, then verify `HEAD == origin/main` and repo clean.

## Phase 2 sequencing lesson

Do not lump every markdown file into “low risk”. Separate text that no code consumes from markdown/templates that runners still reference.

Recommended sequence after the SOUL phase:

1. **Package 1 — safe text cleanup**: archive `contracts/gb-cc-en.md`, cite the new `references/category-experience-map.md` in `cc-rec.md` and `cc-p1.md`, and trim redundant reference pointers from SKILL.
2. **Package 3 — runner fallback**: remove/neutralize the REC runner fallback to `templates/rec-{template_key}.md`, with dry-run validation.
3. **Package 2 — templates**: only after fallback is removed or proven unused, archive `templates/rec-gb-cc-en.md` and `templates/p1-gb-cc-en.md`.
4. **Package 4 — AGENT.md routing**: rewrite routing to REC+P1/contract-based flow after runtime/code paths are safe.

Reason: `scripts/mgs-rec-runner.py` currently prefers `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md`, but still contains a legacy fallback to `/root/mgs-agent/skills/content-generate-rec-p1/templates/rec-{template_key}.md` if the universal contract is missing. `data/sites.json` still has `eggbev.template_key = gb-cc-en`. Therefore template archival is not the first “low risk” cleanup.

## Current path facts from the audit

- `REC_UNIVERSAL_CONTRACT = /root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md`
- `REC_TEMPLATES = /root/mgs-agent/skills/content-generate-rec-p1/templates`
- `data/sites.json`: only `eggbev` had `template_key`, value `gb-cc-en`.
- `mgs-p1-runner.py` points directly to `contracts/cc-p1.md` in the inspected state; no equivalent P1 template fallback was found in the initial grep.

## Review habit

When Rodolfo or another agent supplies scripts for these phases, Zeus should review against the live VPS state before applying: current SHA, paths, side effects, secret scan, `git diff --check`, whether the change is purely additive/textual or affects runtime/code, and whether auto-push committed staging files accidentally.