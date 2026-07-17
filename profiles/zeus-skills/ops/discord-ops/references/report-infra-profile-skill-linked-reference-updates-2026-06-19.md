# REPORT-INFRA — profile skill updates with linked references and evidence notes

Use when another MGS agent reports an update to one profile skill/reference, but validation reveals the changed workflow points to another newly-created or modified reference file, imported thread evidence, screenshots/contact sheets, or a known pending caveat.

## Pattern validated

During agente legado Creative Ops updates, the reported file was:
- `creative-brief-handoff/references/video-variation-gpt-grok-workflow.md`

Validation showed the workflow now linked to an additional precedent file:
- `creative-brief-handoff/references/video-gpt-grok-precedent.md`

The first semantic check failed because the reported file did not contain the thread ID directly. The correct interpretation was not “report invalid”; the workflow delegated the detailed precedent to the linked reference. Zeus then validated both files, the imported read-only thread snapshot, and screenshot/artifact evidence before inventory/commit.

## Processing checklist

1. Run `sync-souls.sh` first so runtime profile skill files and `/root/mgs-agent/profiles/<agent>-skills/...` are in sync.
2. For every path explicitly reported, verify:
   - runtime file exists;
   - versioned file exists;
   - runtime/versioned SHA match.
3. If semantic validation fails on the reported file, inspect nearby links/references before rejecting the report. A class-level workflow may point to a support file that carries the session-specific detail.
4. If the support file is newly created or modified and is part of the reported workflow, include it in the same scoped commit and inventory update. Do not leave a dangling untracked reference.
5. Validate evidence without dumping large media:
   - imported Discord thread files exist and message count is plausible;
   - screenshot/contact-sheet/artifact directory exists and file count is compactly recorded;
   - semantic rules claimed in the report are actually present in the reference text.
6. Run secret scan on the versioned docs/scripts being staged. Reference paths and thread IDs are OK; literal tokens/cookies are not.
7. Update `infra-inventory.json` under `profile_skill_references[]` with each relevant reference file, including:
   - `source_thread_id` when the rule came from a thread;
   - `validation` summary;
   - `known_pending` when the report explicitly says a recipe/caveat remains unresolved.
8. Patch `infra-discovery.sh` to preserve any manual inventory section introduced or used by the report, e.g. `profile_skill_references[]`, `runtime_artifacts[]`, not just `system_packages[]`.
9. Stage only the scoped files: inventory, reported reference(s), linked reference(s) that are part of the workflow, and preservation script if changed. Leave unrelated sync-souls outputs, generated assets, thread imports, screenshots, browser profiles, and other agents’ files unstaged.

## Pitfalls

- Do not require every semantic fact to live in the one reported file. Follow class-level references.
- Do not commit imported Discord snapshots or generated screenshots/contact sheets; they are validation evidence, not versioned infra.
- Do not ignore a reported `Risco/pendência`; store durable caveats as `known_pending` in the inventory entry or audit log.
- If a file was created through `skill_manage` in another profile, validate both runtime and versioned copies before ACK. Runtime-only success is not enough for MGS auditability.
