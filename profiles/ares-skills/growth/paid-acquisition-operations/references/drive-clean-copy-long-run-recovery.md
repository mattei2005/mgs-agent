# Drive clean-copy long-run recovery pattern

Use this reference when an Ares Drive creative clean-copy queue runs for hundreds of Canva exports and needs resumable execution, OAuth refresh, and post-run reconciliation.

## Durable lessons

1. **OAuth access tokens expire during long queues.** A real-user OAuth refresh token may be valid, while the short-lived access token used by the current process expires mid-run. Treat `HTTP Error 401: Unauthorized` during a long Drive upload as a recoverable item-level failure: refresh access token, update the Drive client token, and retry the same queue item once before recording an error.
2. **Do not run duplicate executors in parallel.** Before starting or resuming a full queue, check for an existing executor process for the same queue. If one exists, monitor/wait instead of launching another. Parallel runs can upload the same queue IDs twice.
3. **Report rows are not the source of truth by count.** Reconcile final state by `queue_id`: `unique_uploaded = distinct queue_id with status=UPLOADED`, not raw `UPLOADED` row count. Error rows from prior attempts and duplicate upload rows may remain in the append-only audit CSV.
4. **Post-run duplicate cleanup is Drive-state work.** If parallel overlap created extra destination files for the same queue ID, keep the first successful destination ID and move extra destination IDs to Drive trash only after final reconciliation. Record a cleanup JSON with kept/trash IDs and status.
5. **MP4 structural fields are not privacy metadata.** For video verification, fields such as `PixelAspectRatio`, `AudioChannels`, `AudioSampleRate`, `VideoFrameRate`, etc. should not block `clean=true` if ExifTool shows no harmful privacy tags.
6. **ZIPs remain manual-review.** Do not attempt automatic metadata cleaning/upload for ZIPs in this flow; keep them out of the automated clean-copy path.

## Recommended final reconciliation fields

```text
queue_total
auto_total
manual_review_total
unique_uploaded_auto
remaining_auto
report_rows
report_status_counts
upload_duplicate_queue_ids_count
extra_uploaded_report_rows_due_to_retries_or_overlap
error_rows_total
queue_ids_with_errors_total
manual_review_queue_ids
missing_auto_queue_ids
```

## Completion criteria

The job is complete when:

- `unique_uploaded_auto == auto_total`;
- `remaining_auto == 0`;
- manual-review items are explicitly listed;
- any duplicate destination files from overlap are either absent or moved to trash with evidence;
- `UPLOAD_CANVAS` originals were never modified in place.
