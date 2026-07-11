# Human upload → READY Drive handoff

Use this reference when Kelly/Geizian/gestor uploads a creative directly in Discord and asks Hera to organize it in `READY` for Ares.

## Durable pattern

1. Treat the Discord message as a valid human upload only when it includes: país, vertical, língua and an attachment.
2. If the live gateway says the file type is unsupported (common with `.mov` / `video/quicktime`), do **not** stop there. Import the thread read-only and inspect `referenced_message.attachments` for the original Discord attachment metadata and CDN URL.
3. Download the attachment with a simple `User-Agent` header; Discord CDN URLs can fail without it.
4. Detect media facts before naming:
   - `ffprobe` for video codec, width, height, duration.
   - Generate a small contact sheet and use vision to identify person/no-person, visible copy, CTA and angle.
5. For CC Spanish operations, map:
   - Country Mexico → `MX`
   - Language Espanhol → `ES`
   - Vertical CC → operation `CC_MX_ES`
   - Vertical story with person → `PV`
   - If the dominant visible claim is a large approved amount/limit, prefer `LIMITE_ALTO` over generic `APROBACION`.
6. Clean metadata server-side before final upload:
   ```bash
   /root/mgs-agent/scripts/clean-creative-metadata.sh clean "$SRC" --out "$DEST" --agent hera
   /root/mgs-agent/scripts/clean-creative-metadata.sh verify "$DEST"
   ```
7. Upload only the clean file to Drive destination:
   ```text
   MGS-CRIATIVOS/{OPERATION}/{IMG|VID}/01_READY/{OPERATION}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
   ```
   Do not create `STORY/FEED/REELS` subfolders; placement belongs in inventory/handoff.
8. Verify the Drive file by fetching metadata after upload (`id`, `name`, `parents`, `trashed=false`, `size`, `webViewLink`). Do not claim uploaded until this check succeeds.
9. Append/update local inventory with origin and use fields:
   ```text
   created_by=KELLY/GEIZIAN/GESTOR/UNKNOWN
   source=HUMAN_UPLOAD
   used_by=ARES or HUMAN
   campaign_owner=Ares/Kelly/etc.
   clean=true
   drive_file_id/webViewLink
   ```
10. Respond with a short operational status block and one handoff mention to Ares only when all required fields and the uploaded/verified clean asset exist.

## Notes

- For Drive writes to Rodolfo's personal `MGS-CRIATIVOS`, use the configured real-user OAuth path when service account quota/My Drive constraints apply. Validate root metadata and upload with the established Drive client/module rather than inventing a new credential flow.
- If Rodolfo updates the Drive OAuth refresh token in 1Password but refresh still returns HTTP 400, check whether the established client is reading a complete stale local credential cache before consulting 1Password. Do not delete or overwrite the canonical cache during a live task. Force one fresh 1Password read through isolated root-only temporary token/credential paths, remove the temporary credential file immediately after minting the access token, then validate Drive root metadata. Remediate canonical cache precedence separately with REPORT-INFRA.
- Keep raw/original upload untouched. The cleaned renamed copy is the organized asset.
- If the sanitizer reports `clean: true` and `harmful_tags: 0`, report only the summary; never dump raw metadata in Discord.
