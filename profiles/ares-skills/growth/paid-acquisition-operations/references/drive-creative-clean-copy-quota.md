# Drive creative clean/copy pipeline — Service Account quota pitfall

Session learning from Ares organizing Canva-exported creatives in `MGS-CRIATIVOS/UPLOAD_CANVAS`.

## Durable workflow

For large batches of creative assets uploaded by Rodolfo/humans:

1. Treat `UPLOAD_CANVAS` as RAW/original. Do not clean, overwrite, delete, or move files there.
2. Inventory Drive recursively first using read-only access.
3. Classify logically before writes:
   - vertical/operation first (`CC_*`, `JOBS_*`, etc.)
   - format (`IMG`/`VID`)
   - placement (`FEED`, `STORY`, `LANDSCAPE`, `UNKNOWN`)
   - language (`EN`, `ES`, `DE`, etc.)
   - status (`00_REVIEW`, `01_READY_CANDIDATE`, etc.)
4. Deduplicate by checksum before processing. Keep a skipped-duplicates report.
5. Clean metadata only on the copied/final artifact, not on RAW.
6. Upload cleaned files to final folders and write an execution report with source ID, destination ID, clean hash, and status.

## Metadata sanitizer notes

The MGS sanitizer lives at:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh
```

Canonical single-file flow:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/raw.mp4 --out /path/to/clean.mp4 --agent ares
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/clean.mp4
```

For MP4, ExifTool is the privacy gate. `mat2 --show` may still report structural MP4/container fields such as bitrate, major brand, track IDs, color profile, dimensions, and frame rate after privacy metadata is stripped. Those should not be treated as campaign-blocking personal/privacy metadata if ExifTool harmful tags are zero and `verify` returns `clean: true`.

## Google Drive Service Account quota pitfall

A Google Service Account shared into a normal **My Drive** folder can have permissions like:

```text
can_add_children=true
can_edit=true
can_modify_content=true
```

but uploads can still fail with:

```text
403 storageQuotaExceeded
Service Accounts do not have storage quota. Leverage shared drives, or use OAuth delegation instead.
```

This means read, folder creation, and some metadata operations may work, but file upload to My Drive is blocked because Service Accounts do not own storage quota there.

## Durable fix options

Preferred for MGS batch creative automation:

```text
Option                     Use when
--------------------------|--------------------------------------------------
Shared Drive              Best for long-running agent automation with Service Account upload
OAuth user delegation     Use when files must remain in a user's My Drive
Manual upload             Avoid for large batches; last-resort only
```

Operational recommendation: if Ares must upload cleaned creative files automatically, place `MGS-CRIATIVOS` in a Shared Drive or configure a real user OAuth flow/refresh token. Do not assume Service Account writer access to a My Drive folder is sufficient for uploads.

## Reporting

Any script/data/Drive automation created for this flow should be reported to `#alerts-infra` using `[REPORT-INFRA]`, with paths, reason, commit/hash, and whether Drive writes were performed or blocked.
