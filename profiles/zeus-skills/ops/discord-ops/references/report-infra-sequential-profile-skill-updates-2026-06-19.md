# REPORT-INFRA sequential profile-skill updates — Ares Meta clone case (2026-06-19)

## Situation

Ares sent multiple `[REPORT-INFRA]` messages in sequence for the same profile skill:

- Runtime skill: `/root/.hermes/profiles/ares/skills/growth/meta-openzedfinanzas-replacement-clone/SKILL.md`
- Versioned mirror: `/root/mgs-agent/profiles/ares-skills/growth/meta-openzedfinanzas-replacement-clone/SKILL.md`
- New reference files under `references/` for Elena full clone/token learning and attribution-setting probes.

`sync-souls.sh` also surfaced unrelated Ares audit JSONs and reference files from the same broader workstream. Those were not part of each specific report and had to remain unstaged.

## Correct processing pattern

1. Validate runtime files exist and hashes match the report:
   - `sha256sum <runtime SKILL.md> <runtime reference>`
   - `stat` for size/mtime
   - run a pattern-only secret scan; do not print any token-like value.
2. Run `/root/mgs-agent/scripts/sync-souls.sh`.
3. Verify runtime and versioned SHAs match for the reported skill/reference only.
4. Update `infra-inventory.json` in place:
   - update the skill entry SHA/mtime;
   - preserve existing `references[]`;
   - append or update only the newly reported reference entry.
5. Append compact `report_infra_processed` to `events-audit.jsonl`.
6. Stage only:
   - `data/infra-inventory.json`
   - reported versioned `SKILL.md`
   - reported versioned `references/<file>.md`
7. Leave unrelated untracked audit JSONs/references unstaged.
8. Commit and ACK with the commit SHA.

## Pitfall: auto-commit watcher race

During one report, `infra-inventory.json` was auto-committed by the repo watcher before the manual commit command ran. The correct recovery was:

- check `git show --stat --oneline -1 <latest>`;
- verify the latest commit contained the expected inventory paths/diff;
- use that commit SHA in the ACK;
- do not create an empty commit or restage unrelated dirty files.

## Why this matters

Sequential skill/reference reports are common when another agent is learning during an active operational incident. Treat each report as a scoped audit unit. The durable class-level skill can accumulate references, but each chat ACK must correspond only to the reported artifact(s), not the entire dirty worktree.
