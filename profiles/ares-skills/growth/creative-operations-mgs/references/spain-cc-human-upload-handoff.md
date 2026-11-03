# Spain CC human upload → Ares classification → Ares handoff

Use this reference when Kelly/Geizian/gestor uploads Spanish credit-card creatives and asks whether Ares or Ares should apply the agreed rules.

Current storage precedence: use `flat-upload-intake.md`, the active flat binding and canonical archive resolver. MGS is intake/staging only; permanent common stock is `MGS-ARQUIVO/CRIATIVOS/CC_ES_ES/{IMG|VID}/01_READY/`, while explicitly requested manager delivery uses registered Exclusivos. Sender identity alone does not select an exclusive folder. Preserve RAW/source IDs with the existing same-ID maintenance and no DELETE. Ares owns both creative treatment and later authorized Campaign Ops; old wording about notifying/handoff to Ares does not authorize another bot, writer or a campaign.

## Responsibility split

```text
Ares applies directly
─────────────────────
- Validate required intake: país, vertical, língua, attachment.
- Detect media facts: IMG/VID, dimensions, aspect ratio, placement.
- Classify angle and P_ORIENT from the asset itself.
- Clean metadata server-side.
- Upload the clean renamed copy into READY.
- Verify Drive metadata/link.
- Send one clean handoff to Ares only after the Drive asset is verified.

Ares applies
────────────
- Campaign/test rules from Ares' own thread.
- Ads execution, budgets, placements, campaign setup and performance feedback.
```

If Drive upload or verification is blocked, do **not** mention Ares yet. Report the blocker and the exact next step to unblock, then handoff only after the clean asset is actually in READY with a verified Drive link.

## Spain CC mapping

For intake like:

```text
País: ESPANHA
Vertical: CC
Língua: ES
```

Map to:

```text
country=ES
operation=CC_ES_ES
language=ES
destination=MGS-ARQUIVO/CRIATIVOS/CC_ES_ES/{IMG|VID}/01_READY/
```

For vertical 1080x1920 static creatives with no person:

```text
format=IMG
placement=STORY
aspect_ratio=9:16
p_orient=NV
```

## Angle examples for CC_ES_ES

Use the same class-level taxonomy pattern as CC_US_ES unless Rodolfo/Kelly define a more specific dictionary.

```text
Dominant message                                           angle
─────────────────────────────────────────────────────────  ────────────
6.000 € / 15.000 €, “más crédito”, “más margen”, limit     LIMITE_ALTO
“respuesta rápida”, “menos espera”, “aprobación rápida”    secondary APROBACION / urgency note
“sin papeleo”                                              note only unless it is the dominant hook
```

Do not classify these as `SIN_VERIFICACION` unless the creative explicitly says no verification/no credit check/sin consulta or equivalent.

## Naming examples

```text
CC_ES_ES_IMG_LIMITE_ALTO_NV_08.png
CC_ES_ES_IMG_LIMITE_ALTO_NV_09.png
```

Keep status out of the filename; status lives in the folder/inventory.

## Compliance/localization notes

- Euro amounts are expected for Spain; do not flag `€` as a US localization issue when the operation is `CC_ES_ES`.
- Spanish creative with English disclaimer is not an upload blocker, but mark it as an attention item: disclaimer language may need Spanish localization depending on campaign/compliance rules.
- Claims like “hasta 15.000 €”, “empieza desde 6.000 €”, “100% seguro”, “aprobación rápida” or “respuesta rápida” are usable only with subject-to-approval framing and should be passed to Ares as claim/risk notes, not silently ignored.

## Authentication failure — superseding the historical personal-OAuth recovery

The earlier instruction to restart a personal Google Drive OAuth/refresh-token flow is retired. Agents must use only the canonical Service Account via `mgs_google_workspace_auth.py`; the approved isolated owner connector is not an agent-auth fallback. On an auth failure, retain local media, request IDs and evidence; diagnose the exact canonical SA or isolated-connector boundary and recover only within existing authority. Never claim upload/delivery before exact native readback, switch identities, request a personal login, alter credentials/ACL, or replay a landed upload to repair a verifier. Credential/permission changes retain their explicit gates.