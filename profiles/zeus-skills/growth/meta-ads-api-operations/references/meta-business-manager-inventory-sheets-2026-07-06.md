# Meta Business Manager inventory + Google Sheets export — 2026-07-06

## Context

Rodolfo asked whether existing 1Password Meta tokens could inventory a Business Manager: ad accounts, people connected to each ad account, datasets/pixels, and pixel ↔ ad account relationships, then write the result into a provided Google Sheet.

## Token capability result

1Password items tested without exposing token values:

```text
Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN
  Usable: yes
  Permissions: ads_read/ads_management/business_management granted
  Visible BM: Digital Trust / 155263197283282

Token Meta API - Contas de Anuncio Meta
  Not sufficient: business_management declined

Token Meta API - 00 - ANUNCIANTE - Marcos Silva Arruda - OPENZED SPAIN
  Not usable at the time: OAuthException 190 / subcode 459 checkpoint/login required
```

## Durable workflow lessons

### 1. Always paginate BM inventory edges

Do not treat the first Graph edge response as the total. Initial reads returned misleading partial numbers; full pagination corrected the counts.

Observed with Alana token:

```text
business_users      27 direct BM users
system_users        3
owned_ad_accounts   186
client_ad_accounts  10
total ad accounts   196
owned_pixels        100
client_pixels       1
```

User corrected the initial undercount: UI showed more than 160 ad accounts and 141 users. That correction was valid: the first count was page/edge partial, not final.

### 2. “Users in BM” can mean different Meta surfaces

`/{business_id}/business_users` returns direct BM people with e-mail (27 in this session), not necessarily the UI total Rodolfo sees in access management. To approximate operational access, scan `/{act_id}/assigned_users?business={business_id}` across all owned/client ad accounts and dedupe users.

Observed scan result after full account traversal:

```text
ad accounts processed for users   196
ad account/profile rows           900
unique assigned users seen        96
accounts with zero users          0
```

E-mail caveat: assigned_users returns name/ID/tasks, but not e-mail. E-mail was only available for users returned by `business_users`; leave e-mail blank when Meta does not expose it.

### 3. Pixel/dataset source of truth

For the Meta UI “Data Sources → Datasets & pixels” view, Graph API exposed the usable surface via pixel edges, not separate dataset edges in v20.0.

Use:

```text
/{business_id}/owned_pixels
/{business_id}/client_pixels
/{act_id}/adspixels
```

In this session, dataset-like endpoints such as `owned_datasets`, `client_datasets`, `owned_data_sets`, `client_data_sets` returned unknown-path errors. Do not hard-code those as unavailable forever; treat pixels as the current working API route for this audit class.

### 4. Required sheet tabs for Rodolfo’s requested export

When exporting this audit to a Google Sheet, create exactly the requested operational tabs unless a summary tab is explicitly requested. In this session a temporary `Resumo BM` tab was created for validation and then deleted to keep the sheet clean.

Final tabs:

```text
Contas x Perfis
  Nome da conta de anúncio
  Número da conta de anúncio
  Perfil conectado
  E-mail do perfil

Pixels x Contas
  Dataset/Pixel
  Pixel ID
  Conta de anúncio conectada
  Número da conta de anúncio
```

Verification after write:

```text
Contas x Perfis  900 rows excluding header
Pixels x Contas  223 rows excluding header
Meta API errors  0
```

### 5. Rate-limit handling

Full BM scans require slow pagination and per-account edge traversal. Use bounded sleeps/throttle; do not hammer `assigned_users` and `adspixels` across 196+ accounts at normal cron speeds. For long runs in `#alerts-infra`, run background without `notify_on_complete`, then poll/wait manually and summarize only final counts.

## Suggested implementation shape

A reusable audit script should:

1. Resolve a candidate token from 1Password without printing it.
2. Validate `me`, `me/permissions`, `me/businesses`.
3. Select target BM by ID/name.
4. Page all `owned_ad_accounts` and `client_ad_accounts`.
5. Page all `business_users` for e-mail map.
6. For each account, call `assigned_users?business={business_id}` and join e-mails when available.
7. Page `owned_pixels`/`client_pixels` for inventory counts.
8. For each account, call `adspixels` for pixel ↔ account mapping.
9. Write two Google Sheet tabs and verify readback row counts.
10. Keep local sanitized audit JSON with counts/errors only; never store token values.
