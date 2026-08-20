# Ads Manager video evidence for `31/3858385` (2026-08-20)

## Why this reference exists

Use this when Meta API writes return `OAuthException code=31`, `error_subcode=3858385`, while Ads Manager appears usable and the operator supplies screen recordings of manual creation or cloning.

## Validated evidence pattern

Two screen recordings from the same ad account were inspected with representative frames plus Portuguese audio transcription:

- A fresh-build walkthrough configured Sales/CBO, USD 30, highest volume, Financial Products and Services, Brazil, website conversion, `SUBSCRIBE`, next-midnight start, Brazil targeting, ad-transparency advertiser `DIGITAL TRUST`, creatives, copy, CTA and URLs.
- A clone walkthrough selected a winning campaign, used native **Duplicate campaign**, renamed the clone, reset the scaled budget to USD 30, scheduled next midnight, enabled copied ads, and updated campaign-specific links/UTMs.

Neither recording proved a successful commit:

- objects remained labeled **Em rascunho**;
- **Publicar** / **Ver prévia e publicar** remained available;
- the fresh-build recording ended before publication;
- the clone recording displayed the exact checkpoint panel:

```text
Confirmando suas alterações
Devido a uma atividade recente (como a localização do login) achamos que
alguém pode ter tentado acessar sua conta sem permissão. Por segurança,
seus anúncios não serão veiculados até que você autentique sua conta.
(#3858385)

Iniciar autenticação
```

## Operational interpretation

1. **A usable editor is not proof that Meta accepted the write.** Draft creation can succeed locally while publish/commit remains blocked.
2. **Visible `Iniciar autenticação` is decisive direct evidence.** It supersedes an earlier screenshot or state record saying no authentication banner was visible. Do not classify the case as API-only while this action is available.
3. Complete the authentication with the Facebook identity associated with the User Access Token whenever possible. If the recording was made by another manager, confirm the logged-in identity before assuming that manager's authentication will clear the token issuer's checkpoint.
4. After authentication, run exactly one Graph `validate_only` probe. Only if it passes should a bounded PAUSED canary proceed.
5. If authentication completes but `31/3858385` persists, then investigate the documented API-only variant and escalate with sanitized error JSON, `fbtrace_id`, app/account IDs and timestamps—never the token.

## Fresh-build versus clone lessons

- The UI clone route preserves material source configuration and is the operational reference: duplicate a valid source, reset budget, set the approved start time, normalize child statuses, rewrite tracking links, and verify the full tree.
- The video also showed `Transparência dos anúncios → Anunciante: DIGITAL TRUST` with the payer-different toggle off. Treat this as evidence that the UI selects a verified advertiser entity. Do **not** assume plain `dsa_beneficiary`/`dsa_payor` text is semantically identical. A sanitized network capture is required before mapping an undocumented UI control to a public API field.
- A generic CHATBOT/Messenger playbook must not be copied into a website-conversion operation. Reuse class-level controls (manifest, lock, idempotency, PAUSED staging, readback, allowlist), but derive destination, promoted object, event, identity and creative payload from the live operation contract.

## Screen-recording review checklist

- Inspect frames and audio together.
- Identify whether the operator used **Create**, **Duplicate campaign**, or child-level duplicate.
- Read the breadcrumb and object cardinality at Campaign / Ad Set / Ad levels.
- Check for **Em rascunho**, **Publicar**, **Conferir e publicar**, unresolved review counters, and authentication panels.
- Do not report manual success unless the post-publication inventory/readback proves committed IDs and statuses.
