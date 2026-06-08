# UPLOAD_CANVAS → organized Drive clean-copy workflow

Use this reference when Rodolfo uploads bulk Canva exports into `MGS-CRIATIVOS/UPLOAD_CANVAS` and asks Ares to organize them for campaign use.

## Correct sequence

1. Treat `UPLOAD_CANVAS` as RAW/original: never delete, overwrite, or clean in place.
2. Build a read-only recursive Drive inventory first.
3. Classify logically before moving anything:
   - vertical/operation (`CC`, `JOBS`, `GAME`, `CAR`, etc.);
   - format (`IMG`, `VID`, `ZIP/OTHER`);
   - placement/size (`FEED` 1080x1080, `STORY` 1080x1920, `LANDSCAPE`, `UNKNOWN`);
   - language (`EN`, `ES`, `DE`, etc.);
   - status (`00_REVIEW`, `01_READY_CANDIDATE`, later testing/winner states);
   - origin/source folder as metadata only.
4. Deduplicate before processing. Prefer the most structured/originally organized row only when MD5 matches; write skipped duplicates to a separate CSV.
5. Create a copy queue with `CLEAN_METADATA_THEN_COPY_KEEP_RAW` for IMG/VID and `MANUAL_REVIEW_NO_CLEAN` for ZIP/OTHER.
6. Only after Rodolfo explicitly approves Drive writes: download each canonical source, clean metadata locally, verify `clean=true`, create destination folders, upload cleaned copy, record destination Drive ID.
7. Stop on recurring quota/auth/clean failures and report with evidence.

## Recommended destination shape

```text
MGS-CRIATIVOS/<OPERATION>/<IMG|VID>/<FEED|STORY|LANDSCAPE|UNKNOWN>/<LANG>/<STATUS>/
```

Examples:

```text
MGS-CRIATIVOS/CC_REVIEW/VID/STORY/ES/01_READY_CANDIDATE/
MGS-CRIATIVOS/CC_REVIEW/IMG/FEED/EN/00_REVIEW/
MGS-CRIATIVOS/JOBS_US_ES/IMG/FEED/ES/01_READY_CANDIDATE/
```

Do not use size as the top-level directory. Vertical/operation remains the primary organizing axis; placement/size is a secondary technical axis.

## Google Drive auth pitfall

A Google Service Account can read and create folders in a shared My Drive folder if granted writer permission, but file upload into a personal My Drive can fail with:

```text
403 storageQuotaExceeded
Service Accounts do not have storage quota. Leverage shared drives, or use OAuth delegation instead.
```

Durable fix options:

- Use OAuth for a real user account that owns/has quota for the target My Drive folder; or
- move the asset operation to a Shared Drive where Service Account uploads are supported.

For MGS Ares, OAuth user mode was added via `.env` with `ARES_DRIVE_AUTH_MODE=oauth`; credentials must remain root-only and never be printed in chat. Future Drive write scripts should preflight and report only sanitized fields:

```text
auth_mode: oauth_user or service_account
storage: my_drive or shared_drive
folder_name: MGS-CRIATIVOS
can_add_children/can_edit: true/false
```

## Metadata sanitizer MP4 pitfall

After `exiftool -all=`, MP4 files still expose structural QuickTime/container fields. These are required for playback and are not privacy metadata. Examples include `MajorBrand`, `Duration`, `VideoFrameRate`, and for audio tracks `AudioFormat`, `AudioChannels`, `AudioSampleRate`.

The sanitizer gate should not treat those structural MP4 fields as harmful after cleaning. For video privacy verification, ExifTool harmful-tag count is the gate; `mat2 --show` may still list structural MP4 fields and should not block `clean=true` when ExifTool harmful tags are zero.

Additional ExifTool groups can appear after cleaning, e.g. `Track1:ImageWidth`, `Track1:ImageHeight`, `Track1:XResolution`, `Track1:YResolution`, `Track1:BitDepth`. These are also structural video/image-stream fields, not privacy metadata. If a single MP4 blocks with a small harmful-tag count after cleaning, reproduce on that exact file, inspect ExifTool output, add only clearly structural tags to the allowlist, then verify the cleaned file returns `clean: true` before resuming the bulk queue.

## Execution guardrails

- `UPLOAD_CANVAS` remains RAW and unchanged.
- Never expose OAuth refresh tokens, client secrets, Service Account JSON, or Drive file IDs unless operationally necessary.
- Before starting or resuming the full executor, check for an existing `ares-execute-creative-copy-clean.py` process. Do not launch a second full executor in parallel; Drive uploads are not globally locked and a brief overlap can create duplicate destination files even if the report is resumable by `queue_id`.
- If a Hermes background session is lost but the OS process is still running, attach monitoring with a lightweight watcher process instead of starting a new executor.
- Record every upload in an execution report CSV with queue ID, source ID, destination ID, hashes, and status.
- Summaries must count unique uploaded `queue_id`s, not raw `UPLOADED` rows, because retries/overlaps can duplicate report rows.
- Use resumable execution: already uploaded queue IDs should be skipped on rerun.
- If duplicate Drive files may have been created, report the risk and consolidate with evidence before deleting anything; do not auto-delete without Rodolfo's confirmation.
- REPORT-INFRA is required when adding scripts/data or persistent Drive automation artifacts.
