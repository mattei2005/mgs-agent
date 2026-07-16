# Canva Connect → Google Drive Creative Sync

Session-derived notes for automating MGS creative organization when designers share Canva folders by manager and assets are mixed by placement/language.

## Viability

Canva Connect API can support a read-only-first pipeline to inventory folders, export designs, classify creatives, and upload exported files to Google Drive.

## Canva endpoints / scopes validated from current docs

| Need | Endpoint | Scope | Notes |
|---|---|---|---|
| List folder contents | `GET /v1/folders/{folderId}/items` | `folder:read` | Returns folders, designs, and image assets. Pagination via `continuation`; `limit` max 100. Docs note video assets are currently not returned as folder items. |
| List designs | `GET /v1/designs` | `design:meta:read` | Can filter/search designs created by or shared with the authorized user. |
| Get export formats | `GET /v1/designs/{designId}/export-formats` | `design:content:read` | Use before choosing PNG/JPG/MP4/PDF, because available formats vary by design. |
| Start export | `POST /v1/exports` | `design:content:read` | Async job. Canva provides temporary download URLs valid for 24h on success. |
| Poll export | `GET /v1/exports/{exportId}` | `design:content:read` | Poll until `success` or `failed`; successful jobs may return one URL per page. |
| Create Canva folder | `POST /v1/folders` | `folder:write` | Not needed for initial MGS sync; avoid write unless explicitly approved. |

Relevant rate-limit signals from OpenAPI: folder item listing and design listing around 100 requests/client-user; export create has stricter limits and documented throttles. Batch exports with backoff and checkpointing.

## Recommended workflow for MGS

1. **Authorize read-only Canva integration** with a user that can access Kelly/manager folders.
   - Minimum scopes for inventory/export: `folder:read`, `design:meta:read`, `design:content:read`.
   - Do not expose OAuth tokens, refresh tokens, client secrets, or cookies in chat.
2. **Inventory first, no downloads yet.**
   - Traverse the root/manager folders using `listFolderItems` with pagination.
   - Save: source folder, manager, item type, Canva ID, design title, timestamps if available, and parent path.
3. **Classify placement/language.**
   - Placement from export dimensions/aspect ratio: square/feed (1:1), vertical/story/reels (9:16), feed vertical (4:5), unknown when ambiguous.
   - Language from folder/name if explicit; otherwise OCR or visual/text analysis. Mark uncertain as `UNKNOWN` / review.
4. **Export designs.**
   - Query export formats per design.
   - Export PNG/JPG for static creatives; MP4 for animated/video designs when available.
   - Poll async jobs; download URLs expire after 24h, so upload to Drive promptly.
5. **Upload to Google Drive** using Service Account when possible.
   - Prefer a shared `MGS-AGENTS/CRIATIVOS` Drive/folder with least-privilege access.
   - Start with Viewer/read checks; Editor/write only after Rodolfo explicitly approves upload.
6. **Produce audit report.**
   - Counts by manager, folder, format, language, placement, exported, uploaded, skipped, failed.
   - Include a review queue for uncertain language/format and any Canva API limitations encountered.

## Drive structure options

Manager-first when Rodolfo/Kelly operationally think by gestor:

```text
MGS-AGENTS/CRIATIVOS/
└── <GESTOR>/
    ├── FEED/
    │   ├── EN/
    │   ├── ES/
    │   └── PT/
    ├── STORIES/
    │   ├── EN/
    │   ├── ES/
    │   └── PT/
    └── REVIEW/
        └── idioma-ou-formato-incerto/
```

Operation-first when syncing directly to ads taxonomy:

```text
MGS-AGENTS/CRIATIVOS/
└── <OPERATION>/
    ├── IMG/
    │   ├── FEED/
    │   └── STORIES/
    └── VID/
        ├── FEED/
        └── STORIES/
```

## Guardrails

- Initial pilot should be **read-only + inventory**. No downloads/uploads/moves/deletes until scope is approved.
- Google Drive writes, Canva folder writes, moving files, or deleting assets require explicit Rodolfo approval.
- Billing/payment is not involved here; if any paid Canva/Drive/API change appears, treat as critical and double-confirm.
- Do not claim full video coverage from folder listing: Canva docs currently say video assets are not returned by `listFolderItems`; exportable designs can still produce MP4 when supported.

## Suggested pilot deliverable

A CSV/Sheet inventory plus a short report:

```text
manager, source_folder_path, item_type, canva_id, title, export_formats, width, height,
aspect_ratio, placement_guess, language_guess, confidence, proposed_drive_path, status, notes
```
