# CAR BR/BR multi-image upload → READY + Ares handoff

Use this reference when Kelly/Geizian/gestor sends multiple Portuguese Brazil car-financing static creatives in Discord and asks Ares to put them in Drive for Ares.

## Durable pattern

Current storage contract supersedes this guide's old Shared-Drive destinations: `UPLOAD MANUAL` is directly below MGS; temporary processing is internal `_PROCESSAMENTO`; permanent stock is in the 30 TB archive. Use `flat-upload-intake.md` and the canonical resolver/owner transport, not a direct SA binary upload to My Drive. General delivery ends at `MGS-ARQUIVO/CRIATIVOS/CAR_BR_BR/IMG/01_READY`; an explicitly requested manager delivery uses the registered Exclusivos folder. Preserve source IDs/RAW through the existing same-ID maintenance, with no DELETE. Ares owns treatment and campaign consumption; there is no second-bot handoff or automatic campaign authorization.

1. Treat the batch as valid when the message includes `País: BRASIL`, `Vertical: CAR`, `Língua: PORTUGUES` and image attachments.
2. Language-code rule for this flow: when the user says only `PORTUGUES` for `País: BRASIL`, use Brazilian Portuguese code `BR`, so the operation is `CAR_BR_BR`. Use `PT` only when Portugal/Portuguese-Portugal is explicitly stated.
3. Detect all images before naming. For typical CAR BR/BR batches in this flow:
   - `1080x1920` → `IMG`, vertical/story placement.
   - no visible human/person → `NV`.
   - operation code → `CAR_BR_BR`.
4. Ares applies the Creative Ops rules directly, without asking for extra authorization for routine Creative Ops tasks:
   - classify angle from visible promise/copy;
   - rename;
   - clean metadata;
   - upload/verify the clean copy only in authorized temporary staging, then archive through the canonical flow and verify permanent delivery at `MGS-ARQUIVO/CRIATIVOS/CAR_BR_BR/IMG/01_READY/` for common distribution;
   - verify Drive metadata after upload;
   - register inventory.
5. Ares should not be asked to do Ares's file hygiene. Ares consumes the verified `READY` assets and applies campaign/test rules only.
6. If Ares needs to be notified, do it silently/background; do not ping Ares in the human thread and do not reply to Ares bot validation/continuation messages there.
7. Source preservation depends on intake:
   - Discord attachment: keep the external source untouched; upload only the cleaned renamed copy.
   - Drive `UPLOAD MANUAL` with explicit **tratar/mover**: validate RAW/clean, archive receipt/ACK and permanent stock; let the existing same-ID maintenance preserve completed staging sources in the archive. READY/LEGACY in `_PROCESSAMENTO` are temporary technical states, not a permanent tree to create in MGS. An explicit copy/keep instruction preserves its original scope; do not delete or move sources ad hoc.

## CAR_BR_BR naming used in this flow

```text
CAR_BR_BR_IMG_{ANGLE}_{P_ORIENT}_{VARIANT}.jpg
```

Example angle labels that worked for BR car-financing creatives:

```text
APROVACAO_FACILITADA
APROVACAO_ONLINE
CARRO_NOVO
CONQUISTE_AGORA
ENTRADA_ZERO
FINANCIAMENTO_FACIL
SCORE_BAIXO
SEM_ENTRADA
URGENCIA
```

Use the dominant visible claim as `ANGLE`. If two pieces share the same angle, increment the variant (`001`, `002`, ...). Do not put READY/TESTING/etc. in the filename; status lives in the folder/inventory.

## Validation checklist

```text
- Dimensions/formats checked for every attachment.
- Metadata sanitizer `clean` + `verify` returns clean=true for every final file.
- Upload is verified by Drive metadata: id, name, parent, size/checksum when available, trashed=false.
- Inventory includes: operation, country, vertical, language, format, p_orient, placement_fit, angle, status, created_by, requested_by, source, used_by, campaign_owner, clean, drive_file_id/webViewLink.
- If Ares needs the package, notify silently/background only after Drive links are verified; do not create Ares ↔ Ares ping-pong in the human thread.
```

## Handoff wording

Use short wording that separates responsibilities:

```text
Ares aplicou: classificação, naming, metadata clean, READY e inventário.
Ares aplica: regras de campanha/teste/performance quando puxar os assets.
```
