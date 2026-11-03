# Human upload → READY Drive handoff

Use this reference when Kelly/Geizian/gestor uploads a creative directly in Discord and asks Ares to organize it in `READY` for Ares.

## Current storage precedence

Entrada vigente: arquivos diretamente em UPLOAD MANUAL no MGS; _PROCESSAMENTO é temporário. Estoque permanente nos 30 TB, resolvido por ares_archive_storage/ares_archive_locations; não exigir driveId de Shared Drive em My Drive. Pedido geral da Kelly sem destinatário segue common/IMG ou VID/01_READY; entrega própria/gestor expresso segue Exclusivos e uso real confirmado segue Usados. Preservar RAW, mesmos IDs, bytes, reservas, elegibilidade e duplicatas. Agentes usam somente SA canônica; transporte owner isolado não é fallback de identidade. Upload não autoriza campanha ou exclusão. Anexo Discord continua fonte externa; não fabricar um flat request para um arquivo fora da entrada. O manifesto original/canônico continua dono desse intake; validar a rota de arquivo antes de prometer entrega. Não exigir reupload, segundo bot ou novo tratamento para corrigir só armazenamento.

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
   /root/mgs-agent/scripts/clean-creative-metadata.sh clean "$SRC" --out "$DEST" --agent ares
   /root/mgs-agent/scripts/clean-creative-metadata.sh verify "$DEST"
   ```
7. Upload the verified clean file only through authorized SA staging and the existing isolated archive/stock lane; independently validate the permanent destination below. Do not send SA binary uploads directly to My Drive:
   ```text
   MGS-ARQUIVO/CRIATIVOS/{OPERATION}/{IMG|VID}/01_READY/{OPERATION}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
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
10. Respond in the original human thread only after full verified delivery, with final links, counts and complete original-to-final map. Ares is the same executor of both stages; no self-mention, second-bot handoff or campaign authorization is implied.

## Notes

- For agent writes/auth use only the canonical SA. Require Shared-Drive driveId for exact staging targets; require approved owner/root/parent, provider/stock IDs, receipt/ACK and full hashes for the permanent archive. Resolve live paths rather than recreating the old Shared-Drive tree.
- The old personal-OAuth cache/refresh-token precedence workaround is retired. Never restore token-only/client-cache files, choose another identity or bypass an auth guard. Diagnose the canonical SA or approved isolated-owner boundary; credential/ACL changes retain their gates. Preserve request/media evidence and recover only the missing authorized step.
- Keep raw/original upload untouched. The cleaned renamed copy is the organized asset.
- If the sanitizer reports `clean: true` and `harmful_tags: 0`, report only the summary; never dump raw metadata in Discord.
