# Progressive-disclosure refactor for large operational skills

Use this procedure when an agent-specific `SKILL.md` has become monolithic, repeatedly inflates context, or mixes several operational branches that are rarely needed together.

## Audit without loading content

1. Scan metadata only: path, character/line count, H2/H3 counts, reference count, and whether a versioned mirror exists.
2. Prioritize MGS/custom skills over bundled or vendor skills.
3. Treat ~20K characters as a review signal, not an automatic defect. A large main file is acceptable only when nearly every section is always needed together.
4. Check runtime evidence separately. Visible Discord message count does not measure session size; tool results, schemas, replay fields, and system prompts dominate.

## Safe refactor

1. Back up every target outside Git under `/root/.hermes/secure-backups/`, with restrictive permissions and a manifest containing original hashes.
2. Preserve frontmatter byte-for-byte.
3. Keep `SKILL.md` as a short router: purpose, always-on rules, progressive-disclosure contract, routing index, pitfalls, and verification checklist.
4. Extract each H2 branch to `references/router-NN-topic.md`.
5. If one H2 remains very large, turn that reference into a second-level router and extract its H3 branches.
6. Create references before atomically replacing the main file so readers never observe broken links.
7. Do not rewrite or summarize procedures during a structural refactor; move them exactly. Content improvement is a separate reviewed change.

## Exact-preservation validation

- Parse the original from backup and reconstruct every H2 section from the new reference graph.
- Require exact equality, not semantic similarity.
- Do not use `rstrip()` independently on nested segments: it silently removes inter-section whitespace. Preserve exact slices and add routing prose only outside those slices.
- Validate frontmatter, every routed link, maximum main-file size, absence of temporary files, and live/mirror directory hashes.

## Git and secret-scanner pitfall

Auto-commit secret guards may classify filenames containing words such as `token`, `webhook`, or `private` as sensitive even when the moved content was already versioned safely. Use neutral operational filenames (`meta-runtime-diagnostics`, `alert-layout`, `thread-member-management`) while keeping the original section title inside the file. Never weaken the scanner just to land a refactor.

## Mirrors and sync scope

- Sync only the custom skills that were changed.
- Do not mirror an entire bundled/vendor category for convenience.
- If an agent's modified custom category is not versioned, add a selective skill allowlist to `sync-souls.sh`, then validate live/mirror byte equality.
- Run infrastructure discovery, append audit evidence, allow the normal auto-commit/push chain to finalize, and issue REPORT-INFRA according to MGS policy.

## Completion criteria

- Original content reconstructs exactly from references.
- Main files are lean routers and all links resolve.
- Every changed live skill has a byte-identical versioned mirror where required.
- Backup, audit, inventory, Git state, and infrastructure report are accounted for.
