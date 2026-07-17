# Drive final organization, 00_REVIEW backlog, and promotion workflow

Use this reference when a large `UPLOAD_CANVAS` creative organization has reached the final Drive copy stage and there are leftover review items.

## Durable lessons

- `UPLOAD_CANVAS` stays RAW/original. Final organization uses clean copies in organized folders.
- `01_READY_CANDIDATE` means the asset has enough visual/classification evidence to be reviewed for campaign readiness, not that it is already approved for campaign use.
- `00_REVIEW` is still useful: copy cleaned versions there instead of leaving ambiguous assets only in RAW. This gives Rodolfo a clean review backlog while preserving originals.
- When promoting a cleaned file from `REVIEW/.../00_REVIEW` to `.../01_READY_CANDIDATE`, move/rename the existing cleaned Drive file. Do **not** re-clean/re-upload from RAW unless the cleaned copy is missing or invalid.
- The executor `/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py` expects queue rows to include `original_filename`, `destination_filename`, `destination_folder`, `source_drive_id`, `queue_id`, and `queue_action`. If you build a custom queue from another report, include `original_filename` even if you also carry `current_filename`.
- Before executing a queue, validate destination filenames use 3-digit variants (`001-999`), never 2-digit variants.
- After execution, validate by comparing queue rows to report rows: every `queue_id` must have `status=UPLOADED`, errors must be 0, and `dest_drive_id` count should match uploaded rows.

## Recommended sequence

1. Generate/refresh inventory after any Drive write.
2. Build final organization queue for fully classified assets.
3. Execute `clean + copy`, preserving RAW.
4. Validate report: queue rows, report rows, status counts, missing queue IDs, unique destination IDs, and top destination folders.
5. For leftovers, build a `REVIEW/.../00_REVIEW` clean-copy queue and execute it too.
6. Re-review `00_REVIEW` visually. Split into:
   - `PROMOTE_TO_READY_CANDIDATE` — enough evidence after visual/manual review.
   - `KEEP_IN_00_REVIEW` — still ambiguous, wrong vertical, weak confidence, or not campaign-useful.
7. Promote accepted cleaned files by Drive metadata update (`name`, parent folder), not by re-uploading.
8. Report sanitized evidence only: counts, paths, hashes, and status totals. Never expose OAuth/client secrets/tokens.

## Validation checklist

```text
Check                                 | Expected
--------------------------------------|-----------------------------
RAW/UPLOAD_CANVAS                     | Unchanged
Queue rows                            | Equals intended scope
Report rows                           | Equals queue rows
Status                                | All UPLOADED/PROMOTED
Errors                                | 0
Missing queue IDs                     | 0
Destination IDs                       | Unique count equals success count
Variant width                         | 3 digits, 001-999
00_REVIEW semantics                   | Not campaign-ready
Promotion semantics                   | Move/rename cleaned copy
```

## Canonical Google auth handling

If `op item get` hits rate-limit during a long Drive session, do not mark the operation failed. Persist the queue/report paths, then retry with a bounded background process using slow backoff. Do not retry aggressively: repeated 1Password calls extend the block.

The shared executor `/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py` uses only the 1Password item `Google Service Account - MGS Agent` and fails closed when `ARES_DRIVE_AUTH_MODE` is not `service_account`. The former local OAuth caches were retired on 2026-07-17 and must not be recreated as fallback.
