# UPLOAD_CANVAS Drive inventory and organization workflow

Use when Rodolfo uploads Canva/exported creatives into `MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS` and asks Ares to organize by vertical.

## Operational sequence

1. Treat `UPLOAD_CANVAS` as immutable RAW/original storage.
2. Use Google Drive Service Account in read-only mode first.
3. Generate recursive inventory before any Drive write:
   - direct/recursive file counts
   - source folder
   - MIME/extension
   - IMG/VID/ZIP
   - width/height/aspect ratio
   - placement fit: FEED/STORY/LANDSCAPE/UNKNOWN
   - language guess from filename/folder
   - vertical guess from evidence only
   - MD5 duplicates where available
4. If vertical is unclear from names/folders, create visual sample/contact sheets from Drive thumbnails instead of guessing.
5. Use visual classification to mark folders/lots as CC/JOBS/etc. only when evidence is strong.
6. Generate an organization proposal CSV/JSON with proposed destination and confidence.
7. Ask Rodolfo for explicit approval before any copy/move/rename/metadata-clean write in Drive.
8. When approved, copy cleaned outputs to final folders and keep RAW untouched.

## Durable lesson from Canva upload session

A folder named `organized` or a manager folder may still contain mixed verticals. Do not assume all files in a source folder share one vertical unless visual samples support it.

Observed useful classification signals:

```text
Signal type       | Example evidence                         | Vertical
------------------|-------------------------------------------|---------
Credit card text  | credit card approved, tarjeta aprobada    | CC
Credit terms      | limite aprobado, available limit, Visa    | CC
Jobs text         | estamos contratando, vacantes disponibles | JOBS
Jobs terms        | trabajos de almacén, repartidores, $/hora | JOBS
```

## Metadata sanitizer gate

Before any creative becomes a final deliverable, campaign asset, or Drive handoff copy, run the central sanitizer:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/file \
  || /root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/file --agent ares
```

For Drive organization, preferred write behavior after approval:

```text
Action                                Rule
--------------------------------------|---------------------------------------------
RAW in UPLOAD_CANVAS                  keep intact; do not overwrite/delete
Cleaned final copy                    copy to destination folder only after approval
Metadata clean failure                escalate; do not use raw in campaign
Duplicate MD5 groups                  review before duplicating into final folders
```

## Script pattern used in MGS repo

Session-specific scripts were created under `/root/mgs-agent/scripts/`:

```text
Script                                            Purpose
--------------------------------------------------|-----------------------------------------------
ares-drive-upload-canvas-inventory.py             read-only recursive Drive inventory
ares-drive-thumbnail-sampler.py                   read-only thumbnail/contact-sheet sampler
ares-propose-creative-organization.py             proposal CSV/JSON from inventory + visual rules
```

These are implementation examples, not universal requirements. If scripts drift, inspect current repo before running.
