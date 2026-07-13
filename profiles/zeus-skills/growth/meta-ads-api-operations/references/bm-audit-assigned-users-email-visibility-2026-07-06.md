# BM audit: assigned_users email visibility (2026-07-06)

## Context

Rodolfo asked Zeus to audit a Meta Business Manager and populate a Google Sheet with:

- ad accounts → assigned profiles → profile e-mails;
- datasets/pixels → linked ad accounts.

The token candidates in 1Password included:

- `Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN`
- `Token Meta API - Contas de Anuncio Meta` (Roosevelt Mattei)

Both were tested read-only; no credentials were printed.

## Durable findings

### Token checks

Use `debug_token` before drawing conclusions:

```text
GET /debug_token?input_token={token}&access_token={token}
```

The Roosevelt token eventually had:

```text
read_insights          granted
ads_management         granted
ads_read               granted
business_management    granted
```

So a missing standard OAuth scope was **not** the reason e-mails stayed blank in the ad-account assignment export.

### Business users vs assigned users are different surfaces

`/{business_id}/business_users?fields=id,name,email,role` returned only direct `BusinessUser` records with e-mail (27 in this session).

`/act_{account_id}/assigned_users?business={business_id}&fields=id,name,email,tasks` returned assigned profiles for the ad account, but the response omitted `email` even with HTTP 200 and `business_management=granted`.

The omission was reproduced with 10-second retries and no rate-limit error. It is not the same as `code=80004` rate limiting.

### Documentation check

Meta docs checked in-session:

- Ad Account → Assigned Users (`/{ad-account-id}/assigned_users`): reading returns `AssignedUser` nodes; documented added fields include `tasks` and `permitted_tasks`; error table includes `80004` rate limit, but the tested responses were HTTP 200.
- Graph API → Business User (`/{business-user-id}` / `/{business_id}/business_users`): field `email` is documented as “User's email as provided in Business Manager.”

Operational implication: if a profile appears in the BM UI under People/asset assignment but is not returned as an email-bearing `BusinessUser`, the public Graph API path may not expose that email via `assigned_users`. Use browser/UI extraction or inspect the internal BM request if Rodolfo needs every email exactly as visible in the UI.

## Proven BM audit/export endpoints

```text
GET /{business_id}/owned_ad_accounts?fields=id,account_id,name,account_status,currency,timezone_name
GET /{business_id}/client_ad_accounts?fields=id,account_id,name,account_status,currency,timezone_name
GET /{business_id}/business_users?fields=id,name,email,role
GET /act_{account_id}/assigned_users?business={business_id}&fields=id,name,tasks
GET /{business_id}/owned_pixels?fields=id,name,owner_business,last_fired_time
GET /{business_id}/client_pixels?fields=id,name,owner_business,last_fired_time
GET /act_{account_id}/adspixels?fields=id,name,owner_business,last_fired_time
```

Always paginate all edges. In this session, first-page-only logic undercounted the BM; full pagination found 196 ad accounts.

## Google Sheet handling notes from the session

Rodolfo requested these tabs in a provided Sheet:

- `Contas x Perfis`
  - `Nome da conta de anúncio`
  - `Número da conta de anúncio`
  - `Perfil conectado`
  - `E-mail do perfil`
- `Pixels x Contas`
  - `Dataset/Pixel`
  - `Pixel ID`
  - `Conta de anúncio conectada`
  - `Número da conta de anúncio`

When asked to remove profiles from a tab, use Sheets API `deleteDimension` bottom-up by row number, then read back the tab and confirm zero remaining matches.

When asked whether a user is in every account, do not use the already-mutated sheet as source of truth unless Rodolfo explicitly asks for sheet-only validation. Re-query BM/API directly across all ad accounts and write a new tab for missing assignments.

## Reporting style for Rodolfo

Be direct and evidence-first. If e-mails cannot be filled via public Graph API, say:

```text
Não foi rate limit: HTTP 200 nas tentativas, sem code=80004.
O token tem business_management=granted.
O edge assigned_users omite email; email só veio de business_users.
Para todos os emails como na UI, próximo caminho é browser/UI ou chamada interna do BM.
```
