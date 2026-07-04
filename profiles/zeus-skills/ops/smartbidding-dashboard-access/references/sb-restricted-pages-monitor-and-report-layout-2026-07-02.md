# SB/DigitalTRChat restricted pages monitor + report layout (2026-07-02)

## Operational rule

For MGS Messenger restricted-page monitoring, the durable source split is:

- SmartBidding (`Accounts > Messenger > Page`) is the operational filter.
- DigitalTRChat is the source of truth for the *real restriction error and release time*.

A monitor that needs the exact release time must not invent a time from SB. SB exposes `RESTRICTED_UNTIL` as a date only. The hour/minute comes from the newest useful DigitalTRChat report for the page (for example `#2022 ... restricted until July 22 at 7:55 AM`).

## Check sequence

1. Read live SB `/campaigns/Messenger` for MGS scope (`digital-trust + digital-trust-2`, Messenger Page rows).
2. Split rows:
   - `STATUS=Broadcast` and active `RESTRICTED_UNTIL` → already restricted; skip DTR until the restriction expires.
   - `STATUS=Broadcast` without active `RESTRICTED_UNTIL` → eligible for DTR check.
   - `STATUS=On-hold` → report/count separately; do not DTR-check as active send pool.
   - `STATUS=Blocked` → report/count separately; do not DTR-check as active send pool.
3. For eligible active rows only, log into the relevant DigitalTRChat bot user, iterate all top-bar seguradores/accounts, open the latest useful page report, and parse current errors.
4. If a new temporary restriction is found, record:
   - first detected timestamp from the cron run;
   - page name and IDs;
   - bot user (without `@gmail.com` in reports);
   - profile/segurador;
   - exact DTR `restricted until` date + time;
   - report URL if available.
5. If a page is already restricted in SB, do not waste time opening its DTR report until it expires/leaves the restricted set.

## Discord layout approved by Rodolfo

No footer. Keep Discord as executive summary only.

Sections:

1. `Resumo`
2. `Por data/hora de saída`
   - Ordenar cronologicamente por data/hora de saída da menor para a maior.
   - Não ordenar por volume/quantidade de páginas; a função dessa seção é mostrar o que libera primeiro.
3. `Novas restrições detectadas`
4. `Ignoradas nesta rodada`

`Ignoradas nesta rodada` must split:

```text
Já restritas na SB
Status On-hold
Status Blocked
Sem report DTR válido
```

Use `Sem report DTR válido` instead of vague wording like `sem último report útil`.

## Sheet report layout approved by Rodolfo

Destination discussed in-session:

```text
https://docs.google.com/spreadsheets/d/1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY/edit?gid=232316676#gid=232316676
Aba: Report - Paginas Restritas
```

Title:

```text
Páginas Restritas — MGS
```

Category label:

```text
Restrita
```

Recommended sections:

```text
Resumo
Por data de saída
Novas restrições detectadas
Ignoradas nesta rodada
```

Primary detail columns:

```text
Entrou
Página
Usuário bot
Perfil
Sai da restrição
Page ID
FB Page ID
Status SB
Categoria
Observação
```

Do not include a separate `Link da página` column. The `Página` cell itself should be a hyperlink:

```text
=HYPERLINK("https://facebook.com/{FB_PAGE_ID}", "{PAGE_NAME}")
```

Remove `@gmail.com` from the displayed bot user.

## Cron/channel details from initial implementation

Initial SB-only monitor files:

```text
/root/mgs-agent/scripts/monitor-sb-restricted-pages.sh
/root/mgs-agent/scripts/monitor-sb-restricted-pages.py
/root/mgs-agent/data/sb-restricted-pages-monitor.json
/root/mgs-agent/logs/monitor-sb-restricted-pages.log
```

Cron:

```text
0 8 * * * flock -n /var/lock/monitor_sb_restricted_pages.lock /root/mgs-agent/scripts/monitor-sb-restricted-pages.sh >> /root/mgs-agent/logs/monitor-sb-restricted-pages.log 2>&1
```

Discord channel:

```text
1522442220903337984
```

Initial validation found live SB scope of `3,237` rows, `48` active publishers, and `209` restricted Broadcast rows.

Future hardening: evolve the monitor from SB-only into `SB filter + DTR checker + Sheet writer`, preserving the layout and skip rules above.
