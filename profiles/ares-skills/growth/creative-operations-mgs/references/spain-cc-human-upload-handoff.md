# Spain CC human upload → Ares classification → Ares handoff

Use this reference when Kelly/Geizian/gestor uploads Spanish credit-card creatives and asks whether Ares or Ares should apply the agreed rules.

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
destination=MGS-CRIATIVOS/CC_ES_ES/{IMG|VID}/01_READY/
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

## Drive/OAuth blocker handling

If the Drive upload path returns an OAuth `invalid_grant` / expired or revoked refresh token:

1. Keep the cleaned files local and report their paths.
2. Do not claim Drive upload or notify Ares.
3. Ask for/reinitiate the established Google Drive OAuth refresh flow for the Creative Ops/Campaign Ops Drive client.
4. After OAuth is revalidated, upload the clean files, verify Drive metadata (`id`, `name`, `parents`, `size`, `webViewLink`, `trashed=false`), then send the single Ares handoff.

This captures the fix path, not a durable claim that Drive tools are unavailable.