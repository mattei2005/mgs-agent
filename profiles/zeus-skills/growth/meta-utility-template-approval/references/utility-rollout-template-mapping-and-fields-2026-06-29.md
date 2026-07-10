# Utility rollout — template mapping, canary approval, and safe fields (2026-06-29)

## Operational model confirmed by Rodolfo

The SB/Meta Utility rollout is a two-stage workflow:

1. **Canary approval template**
   - Create/upload a new template for one country/vertical/language combination.
   - Put the candidate messages into that new template.
   - Link the canary template to one domain/page only.
   - Open the template editor and click `Run Approval`.
   - Ciro's backend submits the messages to Meta/Facebook; approval results usually return in ~5–10 minutes.

2. **Production template replacement**
   - If the canary result is good, replace the messages inside the current production template for that same country/vertical/language.
   - At midnight, Ciro's backend reads the messages linked to each production template and submits Utility approval across all pages attached to that template.
   - Ciro/Felipe expect that a copy approved on one page usually approves across the rest, but this must still be validated at scale.

Do not replace production templates before canary approval is known. Editing template messages changes the copy/hash and can reset approval state.

## Template inventory mapping

Use the SB `Messenger > Broadcast Template` inventory as the source for existing production templates. Parse the template `NAME` field into:

```text
COUNTRY
VERTICAL
LANGUAGE
COMBO = COUNTRY-VERTICAL-LANGUAGE
```

Common patterns observed:

```text
Newsoun - US-CC-EN/EN-SR - g005-d Kelly      -> US-CC-EN
Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas -> ZA-CC-EN
Cliquet Finanzas - US-CC-ES/ES-ZW - AV ...   -> US-CC-ES
Fincgriffin - US-CAR-EN/EN - JBF - g001-d    -> US-CAR-EN
NAO USAR - Newsoun - MSGS USA CC EN/EN ...   -> US-CC-EN (normalize USA to US)
```

Treat names without an embedded country/vertical/language token, e.g. `teste1`, as manual/unparsed.

## Fields for Phase 1

Rodolfo confirmed Phase 1 should stay simple until Ciro implements image/media support in both front end and back end.

Use only:

```text
TEXT
CTA 1
LINK 1
```

Keep empty unless explicitly approved by Ciro:

```text
IMAGE
CTA 2
LINK 2
TEXT 2
```

Images/media/generic template variants belong to Phase 2 after Ciro releases support in the SB dashboard/backend.

## first_name / profile fields

Do not depend on `{{first_name}}` in Phase 1 Utility copy. Screenshots showed one page rendering the name correctly while another rendered the variable literally or as an empty value, producing broken text such as `, your credit card options...`.

Likely cause: Messenger User Profile API / `pages_messaging` / Page Access Token / page subscription / SB backend profile sync differs by page/app.

Operational default for Utility batches: write copy that works without personalization:

```text
Your credit card options are ready.
Tap below to review your available cards.
```

If `first_name` is reintroduced later, first validate that the specific page/app/backend renders it reliably.

## Automation approach for replacement

For replacing messages inside existing templates, train on one template first:

1. Inspect the template edit screen and/or API payload without saving.
2. Prepare a dry-run diff: existing messages vs replacement batch.
3. Confirm row count, IDs, CTA, links, encoding, and unsupported fields.
4. Apply to one test or explicitly chosen production template only after Rodolfo confirms.
5. Validate by reading back the template from SB UI/API before reporting success.
6. Only then scale by `COMBO`.
