# Meta Business Manager inventory + Google Sheets export — 2026-07-06

## Scope learned

Rodolfo asked for a live Meta BM audit exported into Google Sheets:

- ad accounts + assigned profiles + e-mails;
- pixels/datasets + linked ad accounts;
- check whether specific users are present on every ad account;
- remove/filter rows in the destination Sheet by profile name.

## Durable Meta API findings

Use the live BM/API as source of truth. Do not infer completeness from an existing Sheet.

Known working BM/token in this session:

```text
1Password item: Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN
BM: Digital Trust
Business ID: 155263197283282
```

Do not report token values.

### Counts require pagination

The first Graph response is not the total. Always follow `paging.next` until exhausted.

Edges used successfully:

```text
/{business_id}/owned_ad_accounts?fields=id,account_id,name,account_status,currency,timezone_name
/{business_id}/client_ad_accounts?fields=id,account_id,name,account_status,currency,timezone_name
/{business_id}/business_users?fields=id,name,email,role
/{business_id}/system_users?fields=id,name,role
/{business_id}/owned_pixels?fields=id,name,owner_business,last_fired_time
/{business_id}/client_pixels?fields=id,name,owner_business,last_fired_time
/act_{account_id}/assigned_users?business={business_id}&fields=id,name,tasks
/act_{account_id}/adspixels?fields=id,name,owner_business,last_fired_time
```

Observed shape for Digital Trust after full pagination:

```text
Owned ad accounts   186
Client ad accounts  10
Total ad accounts   196
Owned pixels        100
Client pixels       1
Business users      27
System users        3
```

### Assigned-users pitfalls

`assigned_users` requires `business={business_id}`. Without it Meta returns:

```text
(#100) For field 'assigned_users': The parameter business is required
```

Do not request `role` on `assigned_users`; this field is unsupported there. Use `tasks` instead.

### E-mail limitation

Meta returns e-mail for `/business_users`, but not for `/act_{account_id}/assigned_users`, even if `email` is requested. Directly fetching an assigned user node by ID can return `GraphMethodException / code 100 / subcode 33`.

Operational rule:

- Build an e-mail map from `/business_users` by ID/name.
- Fill Sheet e-mails only when the profile is present in that map.
- Leave other e-mail cells blank and tell Rodolfo why; never invent e-mails.

### Users in all accounts

To answer “is user X in every ad account in the BM?”:

1. Fetch all owned + client ad accounts with pagination.
2. For each account, fetch `/act_{id}/assigned_users?business={business_id}&fields=id,name,tasks` with pagination.
3. Compare by exact displayed `name` unless a stable user ID is provided.
4. Create a Sheet tab listing missing account rows per user.

In the 2026-07-06 audit:

```text
Rodolfo Mattei         present 196/196
Roosevelt Mattei       present 157/196, missing 39
Jeann Carlos Brandão   present 139/196, missing 57
```

## Google Sheets export pattern

Use the canonical MGS Service Account through:

```text
1Password item: Google Service Account - MGS Agent
Project: mgs-core-prod
```

Write tabs by title through Sheets API, but when the user gives a `gid`, resolve `gid -> sheet title` first:

```text
GET /v4/spreadsheets/{sheet_id}?fields=sheets(properties(sheetId,title))
```

For row deletion by profile name:

1. Read target tab values.
2. Find rows where profile column C equals the target name (or exact-cell match if user says “linhas que tem X”).
3. Delete rows bottom-up via `deleteDimension` to avoid index shifts.
4. Read back and verify zero remaining matches.

Tabs created in this session:

```text
Contas x Perfis
Pixels x Contas
Faltando Usuários BM
```

Expected columns:

```text
Contas x Perfis: Nome da conta de anúncio | Número da conta de anúncio | Perfil conectado | E-mail do perfil
Pixels x Contas: Dataset/Pixel | Pixel ID | Conta de anúncio conectada | Número da conta de anúncio
Faltando Usuários BM: Usuário | Nome da conta de anúncio | Número da conta de anúncio | Tipo no BM | Status da conta | Perfis atualmente na conta
```

## Reporting standard

Report concise counts plus validation:

```text
Contas auditadas       196
Linhas gravadas        N
Erros Meta API         0
Readback Sheet         OK
```

If a column is partially blank due to API limitations, say exactly which endpoint lacks the field and how many cells were filled from a real source.
