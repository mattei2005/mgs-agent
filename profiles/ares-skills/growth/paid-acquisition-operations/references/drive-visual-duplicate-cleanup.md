# Google Drive visual duplicate cleanup for UPLOAD_CANVAS creatives

Use this reference when Rodolfo asks Ares to identify/delete duplicate creatives in Google Drive where the files look identical but filenames differ, especially under `MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS/<vertical>/<format>`.

## Operating pattern

1. Treat the request as a two-step cleanup:
   - Step A: read-only duplicate analysis and CSV with `KEEP` / `TRASH_DUPLICATE` recommendations.
   - Step B: trash only after explicit confirmation from Rodolfo.
2. Scope the analysis to the exact folder Rodolfo named. Do not broaden to sibling folders unless requested.
3. Use visual comparison, not just filename or Drive MD5:
   - Download Drive thumbnails or the image itself when no thumbnail exists.
   - Normalize render size/canvas, then compute a pixel hash for exact visual duplicates.
   - Optionally also compute perceptual hashes for near-duplicates, but keep near-duplicate deletion separate from exact visual duplicate deletion.
4. Generate an audit CSV with at least:
   - `group_id`
   - `group_size`
   - `suggested_action` (`KEEP` or `TRASH_DUPLICATE`)
   - `drive_id`
   - `filename`
   - `size`
   - `width`
   - `height`
   - `md5`
   - visual hash field
   - thumbnail path or evidence path
5. Pick one canonical `KEEP` per visual group. Prefer cleaner/export-style names over UI-generated names containing `há`, dimensions, or copied UI text; if uncertain, prefer the shortest stable filename and keep the rest as duplicates.
6. Report counts before action:
   - files analyzed
   - failures
   - duplicate groups
   - files inside duplicate groups
   - suggested keeps
   - suggested trash count
   - CSV path
7. Do not delete/trash during Step A. End with a clear confirmation request for Step B.
8. For Step B, trash only the `TRASH_DUPLICATE` Drive IDs from the approved CSV, then verify visible file count and report before/after.

## Google Drive auth pitfall

Service Account read can succeed while write/trash fails with:

```text
403 insufficientFilePermissions
The user does not have sufficient permissions for this file.
```

If Rodolfo already approved the delete/trash operation and the Service Account write fails, stop and report the exact sanitized capability failure. Correct the canonical Shared Drive role or destination before retrying; never change identity.

## Deletion semantics

Use reversible Drive trash (`PATCH files/{id} {"trashed": true}`), not permanent delete, unless Rodolfo explicitly asks for permanent deletion and passes the critical-operation confirmation flow.

For folder cleanup, trashing parent folders like `CC_REVIEW/IMG` and `CC_REVIEW/VID` is acceptable only when the requested target is the whole folder content and validation shows the parent folder has zero visible children after trash. For duplicate cleanup, trash individual duplicate files, not the entire source folder.

## Reporting format

Use a compact aligned table for Discord. Example:

```text
Duplicadas visuais encontradas

Métrica                                  | Resultado
-----------------------------------------|----------
Arquivos analisados                       | 263
Thumbnails baixados/analisados            | 263
Falhas de leitura                         | 0
Grupos com duplicadas visuais             | 60
Arquivos dentro desses grupos             | 150
Arquivos para manter                      | 60
Duplicadas sugeridas para lixeira         | 90
```

Attach the CSV with `MEDIA:/absolute/path.csv` when useful for Rodolfo's review.

## Infra reporting

Creating durable analysis outputs under `/root/mgs-agent/data/ares/creative-inventory/` requires `[REPORT-INFRA]` to `#alerts-infra`. If the direct Discord send tool lacks access, use the configured alerts-infra webhook from 1Password and report sanitized evidence only (counts and hashes, not credentials).