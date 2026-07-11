# B011 DTR Link Monitor — 2026-07-04

## Context

Rodolfo clarified that B011 is a separate Meta app from B001 and uses the DigitalTRChat/ChatPion connection model, not the B001–B010 `/roles` admin model. A segurador can be **linked to B011** even if `/me/accounts` returns zero pages. Page inventory is separate from OAuth/app linkage.

## Durable Lessons

### 0. B011 source set is all `NO APP = B011`

Correction from Rodolfo after cache cleanup: the operational source for B011 removal classification is every sheet row where `NO APP = B011`, regardless of `Migrado`. If a user is in the sheet for B011 and the DTR/ChatPion + Meta `debug_token` route does not validate linkage to the B011 app, classify it as removed and write `X` in `Removidos acumulado`. When a later cron run validates the user again, clear the `X` automatically and the user returns to the active list.

`Migrado` is informational by default, not a filter. Only require `Migrado=TRUE` when Rodolfo explicitly asks for an active-migrated-only audit.

### 1. Preserve `B011` as its own app key

Bug found: the sheet parser normalized `NO APP = B011` to `B001`, so the cron compared B011 rows against B001 `/roles` and wrote `X` incorrectly.

Required parser behavior:

```text
B001   -> B001
B011  -> B011
B005-2 -> B005-2
B010   -> B010
```

Use a full-match parser that preserves alpha suffixes and hyphen suffixes. Do not use a loose regex that captures only `B001` inside `B011`.

### 2. B011 must not reconcile removals via `/roles`

B011 seguradores are not expected to be app admins/roles. Do not mark `Removidos acumulado` / `X` for B011 based on `/{app_id}/roles`.

Current production behavior: role-based X markers are cleared/prevented for `NO APP = B011`. B011 connection health is owned by the DTR/page-token monitor.

### 3. Account link != page inventory

Rodolfo correction: “Yudi Anggara, Caue Pereira, daí que tem zero páginas, linkado é linkado.”

Correct classification:

```text
Account linked to B011 = debug_token.data.app_id == B011 app_id AND debug_token.data.is_valid == true
Page inventory          = /me/accounts count and /{page_id}/subscribed_apps count
0 pages                 = still linked if debug_token validates
```

Never classify a segurador as unlinked solely because `/me/accounts` returns 0 pages.

### 4. Source set for B011 monitor

Use all sheet rows where:

```text
NO APP  = B011
```

`Migrado` is informational by default, not a filter. Rodolfo corrected this after cache cleanup: if a user is in the sheet for B011 and is not linked to the B011 app, classify it as removed and write `X`; when the cron later validates linkage again, clear the `X` automatically.

### 5. Validation path

For each B011 row:

```text
1. Map `User` email to 1Password item `Digitaltrchat - ...`.
2. Login to DigitalTRChat.
3. Switch to the segurador via `.account_switch` / `POST /social_accounts/fb_rx_account_switch`.
4. Extract active OAuth token from DTR HTML internally only; never print or persist it.
5. Validate account link with Meta `/debug_token` using `app_id|app_secret` from `BOT B011 Token`.
6. Only after link validation, call `/me/accounts` for page inventory.
7. For returned pages, call `/{page_id}/subscribed_apps` to count pages connected to B011.
```

## Production artifacts created

```text
Script: /root/.hermes/profiles/zeus/scripts/b011-dtr-link-watch.sh
State:  /root/mgs-agent/data/b011-dtr-link-monitor-state.json
Cron:   Hermes job 498fb0d95e10, schedule `15 8,13,18,22 * * *` (4 vezes por dia, horário ET; 15 minutos após o monitor Meta para evitar rajada simultânea), deliver=local, no_agent=true
Lock:   /var/lock/b011-dtr-link-watch.lock (skip overlapping run)
Config: 1Password item `BOT B011 Token`
Alert:  B011 channel 1522830283240505385, direct Discord bot post on anomaly/change or explicit live validation
```

The script is silent on OK. It posts direct Discord alerts only on failures/state changes after baseline, or when Rodolfo explicitly requests validation with `MGS_B011_DTR_FORCE_LIVE_ALERT=1`. Dry-run must not save state or send alerts.

## Alert UX contract

B011 must present disconnected profiles the same way Rodolfo reads B001–B010 operationally: if the cron wrote `X` in `Removidos acumulado`, the alert must show those seguradores under `📦 REMOVIDOS ACUMULADOS`, not as a generic error list. For B011, “removed” means the DTR/ChatPion OAuth connection did not validate against the B011 app via Meta `debug_token`; it is not `/roles` removal.

Automatic anomaly alerts and manual forced-live alerts must use the same 3-message shape as B001–B010:

```text
1. Native Discord embed summary: Estado, Linkados, Páginas.
2. Code block: 👥 USUÁRIOS ATUAIS.
3. Code block: ➖ USUÁRIOS REMOVIDOS AGORA + 🆕 USUÁRIOS ADICIONADOS AGORA + 📦 REMOVIDOS ACUMULADOS.
```

For B011, the human-facing columns may still say `SEGURADOR` because the runtime entity is a DTR/ChatPion segurador, but the section labels and 3-message layout must mirror the other 10 app alerts. `👥 USUÁRIOS ATUAIS` must list only currently linked/active B011 accounts; disconnected/X profiles must not appear there with `PENDENTE`, because they already belong under `📦 REMOVIDOS ACUMULADOS`. The accumulated-removals table should include at least `BOT EMAIL`, `SEGURADOR`, `PERFIL ID`, and `MOTIVO`, using the sheet row where `NO APP = B011` as the human-facing source. The current-users block can exceed Discord's 2000-character message limit; split code blocks exactly like `meta-app-roles-watch.sh` instead of posting one oversized message.

## Manual validation alert

Use this when Rodolfo asks to “manda um alerta no B011”:

```bash
MGS_B011_DTR_FORCE_LIVE_ALERT=1 /root/.hermes/profiles/zeus/scripts/b011-dtr-link-watch.sh
```

This must send to channel `1522830283240505385`. Never use `meta-app-roles-watch.sh` for B011 live validation, because that renders the app owner/admin from `/roles` instead of the DTR/ChatPion segurador list.

## Initial validated baseline

```text
Initial active-migrated-only baseline (pre-correction)
Targets B011            19
Linked                   18
Pending                  1 (Kaio Sousa)
Graph pages              199
Connected B011 pages    196
alerts_sent              0
```

After Rodolfo corrected the source-set rule, production default was changed to all `NO APP=B011` rows:

```text
Corrected source set     all rows with NO APP=B011
Targets B011             25
Linked                   18
Pending / X              7
Sheet updates applied    6 new X markers
```

William Nogueira was initially misclassified by an older validation route; after using the corrected account-link rule, he was included as linked in the baseline.

## Pitfalls

- Do not reuse B001–B010 role/admin reconciliation logic for B011.
- Do not treat `0 pages` as unlinked.
- Do not use stale sheet rows with `Migrado=FALSE` as active alert targets unless Rodolfo explicitly asks for all rows.
- Do not expose OAuth tokens, page tokens, app secrets, or authorization codes in Discord/logs.
- O runtime histórico de ~5m20s continua exigindo `flock` não bloqueante, mas a cadência canônica foi reduzida por Rodolfo em 2026-07-10 para quatro vezes por dia (`08:15`, `13:15`, `18:15`, `22:15` ET) após auditoria mostrar consumo excessivo do 1Password. Não restaurar a cadência de ~8 minutos sem autorização explícita e novo orçamento de requests.
- A Facebook OAuth URL like `/dialog/oauth/business/cancel/?app_id=...` can confirm app_id, scopes, and redirect_uri, but it does not contain a usable token/code for monitoring.
