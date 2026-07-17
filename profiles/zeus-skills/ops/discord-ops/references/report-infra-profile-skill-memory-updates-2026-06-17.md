# REPORT-INFRA — Profile skill/memory updates from other agents

Use when another MGS agent reports updates to its own skill library, reference files, persistent memory, or supporting creative/runtime workflow docs.

## Pattern validated

A agente legado report updated:
- runtime skill reference under `/root/.hermes/profiles/legacy-agent/skills/.../references/`;
- versioned copy under `/root/mgs-agent/profiles/legacy-agent-skills/.../references/` via `sync-souls.sh`;
- runtime memory in agente legado profile (not versioned by design);
- supporting scripts and validation artifacts for a YouTube/Shorts reference workflow.

## Zeus processing checklist

1. Validate the runtime file exists and compute metadata (`size`, `mtime`, `sha256`).
2. Run `/root/mgs-agent/scripts/sync-souls.sh` when the report concerns a profile skill/reference that is supposed to be versioned.
3. Verify runtime and versioned skill/reference SHA match after sync.
4. Validate supporting scripts semantically:
   - Python: `python3 -m py_compile <script>`
   - Shell: `bash -n <script>`
   - For secret-backed flows, scan versioned scripts/docs for literal tokens/cookies; path references are OK, secret values are not.
5. Validate the claimed artifact shape without dumping large media/output. Example: count frames/contact sheet in a directory, or read a small status JSON summary.
6. Register runtime-only memory updates in `events-audit.jsonl` as audit context; do not try to version another profile's memory store.
7. Update `infra-inventory.json` with the versioned skill/reference, relevant scripts, and validation summary.
8. Stage only files in the reported scope. `sync-souls.sh` may surface unrelated untracked agente legado/Ares/Atena reference files; leave them unstaged unless they are part of the current REPORT-INFRA.

## Pitfalls

- Do not commit generated frames, contact sheets, browser profiles, cookies, auth stores, or profile memory files.
- Do not treat “memory updated” as a repo file to add. Memory is runtime state; audit the fact, not the content.
- Do not let `infra-discovery.sh` erase manual inventory sections. If a new manual section is introduced, patch discovery to preserve it.
- For creative/reference workflows, validate the class-level workflow plus its reusable scripts, not just that a markdown file exists.
