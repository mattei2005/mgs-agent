# UPLOAD_CANVAS final organization after naming normalization

Use this when Rodolfo says to proceed after taxonomy/naming corrections have already been applied to `UPLOAD_CANVAS` assets.

## Safe sequence

1. Run a fresh Drive inventory after any rename/move.
2. Validate filename compliance separately from visual classification:
   - canonical final names must use `..._{P_ORIENT}_{VARIANT}` with `VARIANT` as **3 digits** (`001-999`);
   - reject/flag any generated destination filename ending in a 2-digit variant.
3. Split inventory into:
   - canonical 3-digit assets ready for final organization;
   - noncanonical RAW assets needing visual review;
   - duplicates by MD5;
   - placement/dimension unknown.
4. For visual review:
   - images: build contact sheets from Drive thumbnails and classify by visual evidence;
   - videos: generate multi-frame timelines first, then overview sheets if the OCR classifier is too slow or insufficient;
   - keep outputs local as CSV/JSON/images, not Google Sheets unless Rodolfo asks.
5. Promote only assets with sufficient visual evidence into the final queue. Keep the rest in `00_REVIEW`/remaining-review CSV.
6. Build one final clean-copy queue combining canonical assets plus visual-review-promoted assets.
7. Deduplicate the final queue by MD5 before write.
8. Before executing `ares-execute-creative-copy-clean.py`, ensure queue rows include the columns expected by the executor, especially:
   - `queue_id`
   - `source_drive_id`
   - `original_filename`
   - `destination_folder`
   - `destination_filename`
   - `queue_action=CLEAN_METADATA_THEN_COPY_KEEP_RAW`
9. Execute with a dedicated report CSV and resume from the report. Do not overwrite the report from failed dry/early attempts.
10. Validate final execution by counting report statuses (`UPLOADED`, `ERROR`, skipped) and checking Drive with a fresh inventory.

## Pitfalls observed

- A queue using `current_filename` but missing `original_filename` causes `ares-execute-creative-copy-clean.py` to error with `'original_filename'` for every row. Fix the queue schema rather than changing Drive state.
- OCR-only video classification can be slow at scale; if it stalls, use timeline overview sheets and visual classification to unblock, while keeping OCR as auxiliary evidence.
- Do not let audit/report CSV rewrites destroy evidence of old names. If normalizing local CSVs, keep a separate audit report with old/new names intact.
- Canonical assets are not automatically campaign-ready; they are ready for final organization/clean-copy. Campaign upload still requires metadata gate and production confirmation.

## Output checklist

```text
Artifact                         | Required
---------------------------------|-----------------------------------------------
Fresh inventory CSV              | yes
Visual review CSV                | yes when noncanonical assets exist
Final queue CSV                  | yes, executor-compatible schema
Remaining review CSV             | yes, for unresolved/low-confidence assets
Dedup skipped CSV                | yes when duplicate MD5 exists
Execution report CSV             | yes for Drive writes
Variant validation               | 0 destination names with 2-digit variants
Infra report                     | required for durable data outputs/writes
```
