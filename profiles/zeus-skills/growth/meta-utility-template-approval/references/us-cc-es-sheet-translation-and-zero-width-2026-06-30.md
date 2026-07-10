# US-CC-ES Sheet Translation + Zero-Width Handling — 2026-06-30

Session learning from Rodolfo's US-CC-ES workflow.

## Trigger

Use this pattern when Rodolfo asks to create a translated country/language approval Sheet tab from an existing Utility Template bank and mentions an existing SB template using zero-width characters.

## Correct Workflow

1. Use the requested source tab as the source of truth, e.g. `US-CC-EN`.
2. Create the target tab, e.g. `US-CC-ES`.
3. Translate only the human-facing copy columns requested:
   - `TEXT`
   - `CTA 1`
4. Preserve these fields exactly unless explicitly told otherwise:
   - `MESSAGE ID`
   - `LINK 1`
   - `DESCRIPTION`, `IMAGE`, `CTA 2`, `LINK 2`, `TEXT 2`
   - UTM placeholders such as `[utm_campaign]`, `[utm_content]`
   - Messenger variables such as `{{first_name}}`
5. After writing, perform Sheet readback and report row count.
6. Separately inspect the named SB template from `/broadcast/Messenger` or the Dash, e.g. `Openzed - US-CC-ES/ES-ZW - AV - g003-d Isliago`, before copying its zero-width behavior.

## Zero-Width Rule From Rodolfo

If Rodolfo asks to apply zero-width:

- Apply it **only to the message body column (`TEXT`)** unless he explicitly says CTA too.
- Use **one U+200B zero-width space between adjacent letters** — not a random or dense pattern.
- Do not insert zero-width inside placeholders: `{{first_name}}`, `{{last_name}}`, `[utm_campaign]`, etc.
- Do not alter `CTA 1`, links, message IDs, or tracking parameters.
- Strip existing zero-width characters before applying a new deterministic pattern to avoid double-insertion.
- Back up the pre-zero-width tab values locally before writing.
- Verify after write:
  - row count matches source;
  - `CTA 1` unchanged;
  - links unchanged;
  - zero-width count exists in `TEXT` only.

## Pitfalls

- Do not infer from the existing SB template that CTA should also receive zero-width; Rodolfo corrected the scope to "apenas nas mensagens".
- Do not modify the SB template during the analysis step unless the user explicitly asks to apply/import there.
- Do not consolidate or dedupe rows when the task is Sheet preparation; preserve the source row structure.
- Translation tools can alter placeholders if not protected first; protect and restore variables/placeholders around translation.

## Reporting Shape

Report in concise ops format:

```text
Aba criada        US-CC-ES
Fonte             US-CC-EN
Linhas            201
Colunas traduzidas TEXT + CTA 1
Links             mantidos
Zero-width        aplicado só em TEXT, U+200B entre letras
Readback          OK
```
