# BM permissions vs Marketing API ad creation block — 2026-06-19

Use this reference when OpenzedFinanzas/Elena ad creation returns `code=31/subcode=3858385` even though Rodolfo says the Ads Manager UI looks normal.

## What was verified

```text
Layer                                  | Evidence / result
---------------------------------------|------------------------------------------------------------
Ad account                             | OpenzedFinanzas-ES-CC-ES-03
Business                               | Digital Trust
User/token identity                    | Marcos Silva Arruda
BM ad-account assignment               | Manage campaigns (ads) ON; View performance ON; Creative Hub mockups ON
BM ad-account full access              | Manage ad accounts OFF, but not required for creating ads
Page asset                             | Elena Santana
Page access for Marcos                 | Facebook access with Anuncios, Content, Messages/calls, Insights
Page control                           | Control absoluto shown in UI
Campaign via API                       | Can be created PAUSED
Adset via API                          | Can be created PAUSED with pragmatic 1-day click attribution
Ad via API                             | Fails before creative validation with auth/checkpoint error
```

## Error shape

`POST /ads` returned:

```text
code/subcode | 31 / 3858385
title        | Autentica tu cuenta
message      | This request requires the user to take a pending action
```

Spanish body said the user cannot create or modify ads until authenticating in Ads Manager, while existing ads continue running.

## Important interpretation

Do **not** assume BM/ad-account/Page permission is missing when this error appears. In this session, UI evidence showed Marcos had sufficient ad account partial access and full control of the Page. The remaining likely classes are:

1. Token/app/API checkpoint that only appears on Marketing API write operations.
2. User/token session state not refreshed after permissions were granted.
3. App/API tier issue (`development_access` observed in response headers).
4. Ad-level payload path triggering a security checkpoint before validation.

## Operational test to separate UI permission from token/API issue

Ask Rodolfo/manager to test manually as the same user (Marcos): duplicate or create one Elena ad, keep it PAUSED, and attempt to complete the publish flow.

```text
Manual duplicate blocks too      | real account/user security checkpoint; finish Meta auth/checkpoint
Manual duplicate succeeds        | likely token/app/API issue; regenerate token after permissions, retest /ads
New token still fails            | investigate app/API access tier or use an approved System User/app path
```

## Communication rule for Rodolfo

When he is frustrated, stop repeating theory and give a short action tree: what was proven, what is still blocked, the one next isolating test, and what each result means.
