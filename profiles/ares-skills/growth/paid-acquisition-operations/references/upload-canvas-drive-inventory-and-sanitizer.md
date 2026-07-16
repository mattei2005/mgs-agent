# UPLOAD_CANVAS Drive inventory + metadata sanitizer pattern

Use this when Rodolfo uploads bulk Canva/exported creatives to `MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS` and asks Ares to organize or prepare them for campaigns.

## Durable workflow learned

1. Treat `UPLOAD_CANVAS` as **RAW/original input**. Do not delete, overwrite, rename, move, sanitize in-place, or treat it as the organized source of truth.
2. Start with a **read-only recursive Drive inventory** via Google Service Account. Capture folder path, filename, Drive ID, MIME, extension, size, MD5, dimensions, aspect ratio, placement fit, created/modified timestamps.
3. Classify only what evidence supports:
   - `format`: IMG/VID/ZIP/OTHER from MIME/extension.
   - `placement_fit`: FEED for 1:1, STORY for 9:16, LANDSCAPE for 16:9/near-landscape, UNKNOWN otherwise.
   - `language_guess`: only from folder/name keywords when clear.
   - `vertical_guess`: only from folder/name keywords when clear; otherwise `UNKNOWN`.
4. Detect duplicate MD5 groups before proposing copy/organization. Bulk Canva exports may contain both raw manager folders and a previous `organized` folder, causing duplicated assets.
5. If most files remain `UNKNOWN`, do **not** invent verticals from manager names. Next step is visual/read-only sampling or thumbnail inspection before any Drive write.
6. Only after Rodolfo approves a plan, copy cleaned outputs into final vertical folders. Preserve `source_top_folder`, original filename, and manager/origin as inventory metadata.

## Metadata sanitizer gate

Approved server-side equivalent of ExifCleaner:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png \
  || /root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Rules:

- Before Ares uses a creative in campaign/test, verify metadata.
- If `clean=false`, clean before upload/use.
- If sanitizer fails, escalate before using the raw file.
- Prefer status/count reporting (`harmful_tags_before`, `harmful_tags_after`, `clean`, output path, audit log), not full metadata dumps in Discord.
- Do not clean/mutate Drive originals directly; clean a local/downloaded copy or staging copy, then upload/copy the clean output after approval.

Canonical sanitizer doc in MGS repo:

```text
/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
```

## Reporting pattern

For inventories/scripts/data created under `/root/mgs-agent/scripts/` or `/root/mgs-agent/data/`, send `[REPORT-INFRA]` to `#alerts-infra`. If `send_message` lacks channel access, use the Alerts Infra webhook from 1Password internally and report only HTTP status, never the webhook URL.

Example report fields:

```text
Ação: criada/modificada
Tipo: script / data
Path: /root/mgs-agent/scripts/<script>; /root/mgs-agent/data/ares/creative-inventory/
Motivo: inventário read-only do Drive MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS antes de qualquer alteração no Drive
Evidência: commit=<sha>; csv_rows=<n>; script_sha256=<hash>; csv_sha256=<hash>
```
