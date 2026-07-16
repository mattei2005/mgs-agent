# Mixed-media Drive intake → READY + LEGACY

Use when an authorized request identifies country, vertical and language and asks Ares to apply rules to a mixed image/video batch in `UPLOAD MANUAL`.

## Durable execution pattern

1. Resolve the live hierarchy from the configured root and confirm `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`; never assume the root ID is itself `CRIATIVOS`.
2. List current source files with Drive ID, name, MIME, size/checksum, image/video dimensions, `ownedByMe` and `capabilities(canDownload,canEdit,canMoveItemWithinDrive,canTrash,canDelete)`. Key all processing by `source_drive_id`, not filename.
   - For the canonical treat/move flow, require the capabilities actually used: download the raw asset, upload the clean copy, and move the source within Drive. `ownedByMe=false`, `canTrash=false`, or `canDelete=false` do not block processing because the original is preserved rather than deleted.
   - Block only when a required capability is absent or the live API rejects that action. Do not require transfer of ownership by default.
   - If Drive has not populated dimensions or duration yet, download and inspect with `ffprobe` or the media decoder; missing Drive media metadata alone is not a rejection or ownership blocker.
   - **Asynchronous-upload stability gate:** a newly announced batch may appear as empty or grow one file at a time while Drive is still finalizing uploads. Before freezing the inventory or starting any write, poll the direct `UPLOAD MANUAL` parent with bounded waits and compare the complete ordered set of `(source_drive_id, name, size)`, not only the count. Require the same non-empty set in at least three consecutive polls spanning a reasonable quiet window (normally 30–60 seconds). If the set changes, restart the quiet-window count. Also require every item to be downloadable and technically probeable before declaring the batch stable.
   - Never interpret an initial empty listing as “nothing to process” when the request has just been sent. Re-query the live parent and inspect recently created accessible media before reporting a blocker; if the queue remains empty through the bounded stability window, report that the upload has not reached the canonical folder yet without inventing completion.
3. Download the stable batch and build compact visual evidence:
   - one labeled image contact sheet;
   - for each video, a labeled strip with frames near 20%, 50% and 80%; inspect a final frame separately if the dominant claim remains unclear.
4. Classify each asset from visible evidence: `IMG|VID`, dominant `ANGLE`, `PV|NV|PH|NH`, placement and exact operation code. Square/feed 1:1 uses `PH|NH` for final naming. For Brasil + CAR + Português without Portugal context, use `CAR_BR_BR`; use `PT` only when Portuguese-Portugal is explicit.
5. Before assigning variants, reconcile each source against the existing lineage inventory and live Drive state, then list live READY filenames and calculate the next numeric variant per exact `(FORMAT, ANGLE, P_ORIENT)` group. Use three digits and preserve the real extension. If the exact group has no prior READY asset, start at `001`; an entirely empty READY folder is valid and is not a blocker.
   - Compute the downloaded RAW SHA-256 and compare it with existing `original_checksum` and `clean_checksum` values before creating a new variant. Use perceptual fingerprints as supporting evidence, not as a substitute for an available exact checksum.
   - An equal filename is not proof of duplication: managers can export different creatives under the same Canva-style name. If the checksum/content differs, keep it as a distinct lineage and record the filename collision in notes. If the exact checksum matches an existing lineage, do not create an independent candidate or consume a new variant; attach the re-upload Drive ID to the existing lineage, validate the existing READY asset, and preserve/move the re-upload to the matching LEGACY parent.
   - User-supplied country, vertical and language define the operation when explicit; filename/folder guesses such as `UNKNOWN` do not override them.
   - Derive `ANGLE` from the dominant, persistent visible claim in the asset language. Normalize it to concise `UPPER_SNAKE_CASE` without translating it (for example, visible English `AVAILABLE LIMIT` → `AVAILABLE_LIMIT`). Keep exact amounts or longer claim text in inventory evidence/notes, not in the canonical filename.
   - For video, confirm claim and person/no-person classification across multiple frames, normally near 20%, 50% and 80%; a single thumbnail is insufficient.
6. For each item, in this order:
   - clean with the canonical sanitizer using `--agent ares`;
   - verify `clean: true` locally;
   - upload only the clean file directly to `{OP}/{IMG|VID}/01_READY`;
   - read back Drive metadata and validate ID, name, parent, `trashed=false`, size and checksum when available;
   - download the uploaded destination, compare SHA-256 with the local clean file and run sanitizer `verify` again;
   - only after those gates pass, move the original from upload to `{OP}/{IMG|VID}/99_LEGACY`, preserving its Drive ID and name;
   - read back the original and validate its new parent.
7. Append inventory entries with source/destination IDs, **exact original filename**, **exact final filename**, operation, classification, clean hash, paths, ownership/use fields and web link. The traceability pair `source_filename → destination_filename` is mandatory and must never be omitted.
8. Final live gate: upload pending count is zero, every batch destination exists in the direct READY parent, every batch source exists in the matching LEGACY parent, all source/destination IDs are unique, and inventory count equals batch size.
9. In the completion response, always show the rename map for every uploaded asset, in processing order:

```text
Nome original  →  Nome final em READY
```

For large batches, split the map into `IMG` and `VID`, but do not replace the per-file mapping with only a filename range. This response map is mandatory because it is the human lookup key for finding the preserved original in `99_LEGACY`.

## Failure discipline

- Stop moving a source if its clean destination has not passed every verification gate.
- On a partial rerun, detect already processed `source_drive_id` and destination IDs before creating another copy.
- Treat an empty intake or missing source IDs during a rerun as a possible completed concurrent execution, not immediately as a failed batch. Before retrying any write, reconcile every expected `source_drive_id` against `assets.jsonl`, the latest execution report, the READY destination IDs and the LEGACY parents. If all sources are complete, switch to verification/reporting; if only some are complete, resume only the missing IDs.
- Serialize batch writes with an operation/batch-scoped lock when parallel Discord sessions can receive the same continuation message. The lock complements, but never replaces, live source-ID and inventory reconciliation.
- Preserve the originating request thread as `thread_id`. A separate thread that only supplies authorization, permission context or a continuation message must be recorded separately (for example, `authorization_thread_id` or notes) and must not overwrite the asset lineage thread.
- Keep status in folders/inventory, never in filenames.
- Do not create placement/language subfolders under READY.
- Report consolidated counts and READY links; do not attach the batch unless explicitly requested.
