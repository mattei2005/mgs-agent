# Mixed-media Drive intake → READY + LEGACY

Use when an authorized request identifies country, vertical and language and asks Hera to apply rules to a mixed image/video batch in `UPLOAD MANUAL`.

## Durable execution pattern

1. Resolve the live hierarchy from the configured root and confirm `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`; never assume the root ID is itself `CRIATIVOS`.
2. List current source files with Drive ID, name, MIME, size/checksum and image/video dimensions. Key all processing by `source_drive_id`, not filename.
3. Download the batch and build compact visual evidence:
   - one labeled image contact sheet;
   - for each video, a labeled strip with frames near 20%, 50% and 80%; inspect a final frame separately if the dominant claim remains unclear.
4. Classify each asset from visible evidence: `IMG|VID`, dominant `ANGLE`, `PV|NV|PS|NS`, placement and exact operation code. For Brasil + CAR + Português without Portugal context, use `CAR_BR_BR`.
5. Before assigning variants, list live READY filenames and calculate the next numeric variant per exact `(FORMAT, ANGLE, P_ORIENT)` group. Use three digits and preserve the real extension.
6. For each item, in this order:
   - clean with the canonical sanitizer using `--agent hera`;
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
- Keep status in folders/inventory, never in filenames.
- Do not create placement/language subfolders under READY.
- Report consolidated counts and READY links; do not attach the batch unless explicitly requested.
