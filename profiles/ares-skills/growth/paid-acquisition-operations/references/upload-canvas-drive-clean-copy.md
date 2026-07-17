# UPLOAD_CANVAS → organized Drive clean-copy workflow

Use this reference when Rodolfo uploads bulk Canva exports into `MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS` and asks Ares to organize them for campaign use.

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
MGS-AGENTS/CRIATIVOS/<OPERATION>/<IMG|VID>/<FEED|STORY|LANDSCAPE|UNKNOWN>/<LANG>/<STATUS>/
```

Examples:

```text
MGS-AGENTS/CRIATIVOS/CC_REVIEW/VID/STORY/ES/01_READY_CANDIDATE/
MGS-AGENTS/CRIATIVOS/CC_REVIEW/IMG/FEED/EN/00_REVIEW/
MGS-AGENTS/CRIATIVOS/JOBS_US_ES/IMG/FEED/ES/01_READY_CANDIDATE/
```

Do not use size as the top-level directory. Vertical/operation remains the primary organizing axis; placement/size is a secondary technical axis.

## Google Drive auth state

The MGS destination is the Shared Drive `MGS-AGENTS` (`0AEwt4Ye690ocUk9PVA`), administered by `support@matteiservicesinc.com`. Only the canonical Service Account is valid, and live preflight must confirm access to this `driveId`.

Credentials must remain root-only and never be printed in chat. Drive write scripts should report only sanitized fields:

```text
auth_mode: service_account
storage: shared_drive
drive_id: 0AEwt4Ye690ocUk9PVA
folder_path: MGS-AGENTS/CRIATIVOS
can_add_children/can_edit: true/false
```

## Metadata sanitizer MP4 pitfall

After `exiftool -all=`, MP4 files still expose structural QuickTime/container fields. These are required for playback and are not privacy metadata. Examples include `MajorBrand`, `Duration`, `VideoFrameRate`, `PixelAspectRatio`, and for audio tracks `AudioFormat`, `AudioChannels`, `AudioSampleRate`.

The sanitizer gate should not treat those structural MP4 fields as harmful after cleaning. For video privacy verification, ExifTool harmful-tag count is the gate; `mat2 --show` may still list structural MP4 fields and should not block `clean=true` when ExifTool harmful tags are zero.

Additional ExifTool groups can appear after cleaning, e.g. `Track1:ImageWidth`, `Track1:ImageHeight`, `Track1:XResolution`, `Track1:YResolution`, `Track1:BitDepth`. These are also structural video/image-stream fields, not privacy metadata. If a single MP4 blocks with a small harmful-tag count after cleaning, reproduce on that exact file, inspect ExifTool output, add only clearly structural tags to the allowlist, then verify the cleaned file returns `clean: true` before resuming the bulk queue.

## Manual Drive reorg / duplicate comparison pitfall

When Rodolfo manually reorganizes Drive after an automated pass, treat his current folder structure as the new source of truth. Example observed structure:

```text
MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS/
├── cartao de credito/
│   ├── imagens/
│   └── videos/
└── emprego/
    ├── imagens/
    └── videos/
```

If he says he moved everything into `00_REVIEW` and asks to delete `01_READY_CANDIDATE`, trash those folders in Drive (reversible trash, not permanent delete) and verify `remaining_ready_candidate_count=0`. Also honor explicit cleanup of obsolete structural folders such as `CC_REVIEW/IMG/FEED/UNKNOWN` after he says files were moved.

For duplicate checks between the manually reorganized `UPLOAD_CANVAS` and cleaned organized folders (`CC_REVIEW`, `JOBS_US_ES`), do **not** rely only on MD5/checksum: cleaned files have different hashes after metadata stripping. Run two layers:

1. exact MD5/checksum match when available;
2. normalized filename match (`__dupnameNNN` and `.metadata-clean` removed, whitespace/case normalized) as the practical comparison for cleaned-vs-raw Drive files.

Report both counts clearly, e.g. `MD5 duplicates=0` can coexist with `normalized-name duplicates=N`; explain that metadata cleaning changes checksum.

## Execution guardrails

- `UPLOAD_CANVAS` remains RAW and unchanged unless Rodolfo explicitly changes the structure and instructs cleanup.
- Never expose Service Account JSON, access tokens or Drive file IDs unless operationally necessary.
- Record every upload in an execution report CSV with queue ID, source ID, destination ID, hashes, status, and error if any.
- Use resumable execution: already uploaded queue IDs should be skipped on rerun.
- Before starting/resuming a long Drive upload, check for an active executor for the exact same script + queue. Do not run parallel uploaders.
- If an overlap happened, compute progress by unique successful `queue_id`, not raw `UPLOADED` rows, then consolidate duplicate impact before deleting anything.
- If Rodolfo gives full autonomy or gets confused by background process noise, reduce technical narration: fix/resume safely and report concise operational status/final results.
- `exit 143` from an intentionally killed duplicate process is not a Drive failure; treat it as cleanup noise unless the real executor stopped.
- For a reusable controller/watcher pattern, see `references/drive-bulk-upload-controller.md`.
- REPORT-INFRA is required when adding scripts/data or persistent Drive automation artifacts.

- Use resumable execution: already uploaded queue IDs should be skipped on rerun.
- If duplicate Drive files may have been created, report the risk and consolidate with evidence before deleting anything; do not auto-delete without Rodolfo's confirmation.
- REPORT-INFRA is required when adding scripts/data or persistent Drive automation artifacts.
