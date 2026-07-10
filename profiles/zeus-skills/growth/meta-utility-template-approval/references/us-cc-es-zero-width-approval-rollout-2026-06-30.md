# US-CC-ES zero-width approval rollout — 2026-06-30

Session learning from Rodolfo correction during US-CC-ES Utility Template workflow.

## Correct sequence

When adapting a language/country tab and preparing production templates:

1. Translate/create the full Sheet tab first from the approved source tab.
2. If zero-width is requested, apply it to the full Sheet/source bank before approval CSV generation.
3. Generate the **full approval CSV** first — not the best 70.
4. Wait for the approval template to finish in SB/Dash.
5. Pull the exact approval-result template from SB and update the Sheet with raw `STATUS`/approval columns.
6. Only after approval results exist: filter `STATUS = APPROVED`, rank by conversion appeal, choose the best 70.
7. Install those 70 into production templates, preserving each target template's exact link sequence.

Rodolfo correction: do **not** generate/send only 70 before approval. Approval probes should contain the full candidate bank (e.g. 201 rows). The 70-message production cut happens after results are known.

## Zero-width density rule

Initial `U+200B` between every adjacent letter was too dense. Preferred operational pattern:

```text
2 visible alphabetic characters + 1 U+200B + 2 visible alphabetic characters + 1 U+200B ...
```

Apply only to `TEXT` when Rodolfo says “apenas nas mensagens”. Do not alter:

- `CTA 1`
- `LINK 1`
- UTM placeholders
- Messenger variables such as `{{first_name}}`

Strip any existing zero-width characters before deterministic reinsertion to avoid double-density.

## Approval result Sheet shape

When Rodolfo gives a completed test template such as `teste-4-us-cc-es-all-201-zero-width-2chars-approval`, read that exact SB template and write raw per-message results into the Sheet tab. Add columns:

```text
STATUS
APPROVED
REJECTED
INVALID_FORMAT
ERROR
REJECTED_REASON
SOURCE_TEMPLATE
TEMPLATE_ID
```

Do not consolidate/dedupe or override statuses. Preserve `MESSAGE_ID` row alignment from the exact test template.

## Production install guardrails

- Use only the matching vertical/language bank (`US-CC-ES` for US Spanish, `GB-CC-EN` for GB English). Do not cross-pollinate languages/verticals.
- Add a lightweight guard before bulk update: reject if selected bank contains obvious wrong-language markers.
- Keep a reusable selected bank file after choosing best 70 so follow-up “also do these templates” requests can reuse exactly the same 70.
- For follow-up missed templates, reuse the same 70 selected bank; still backup each target JSON/CSV and validate via `/broadcast/Messenger`.

## Reporting shape

Report compactly:

```text
Fonte aprovada: US-CC-ES
Aprovadas disponíveis: 158
Selecionadas: 70
Templates atualizados: N
Antes/Depois: 60 → 70
Validação API SB: OK
Links: único vs numerado em ordem
Auditoria: <path>
Backups: <glob>
```
