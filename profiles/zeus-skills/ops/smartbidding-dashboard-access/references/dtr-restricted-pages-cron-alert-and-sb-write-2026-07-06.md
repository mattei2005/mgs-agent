# DTR restricted-pages cron, SB write, and human-readable alert — 2026-07-06

## Context

Rodolfo corrected the restricted-pages monitor design. A page must not be announced as “restrita” from SmartBidding-only state. `RESTRICTED_UNTIL` in SB proves only that SB has a restriction date recorded; the authoritative detection of a new Messenger restriction is the latest DigitalTRChat/Bot Completed report showing `#2022`.

## Canonical workflow

1. Read the live migration sheet.
2. Exclude bot users/seguradores with `Removidos acumulado = X` before logging into DTR.
3. Read live SB Messenger Page rows first only to build a skip-list of pages already restricted: `STATUS=Broadcast` and active/future `RESTRICTED_UNTIL`.
4. Log into DTR for active bot users.
5. Iterate valid top-bar seguradores/accounts and real page selector options.
6. Skip DTR checks for pages already active-restricted in SB; they are already out of send flow.
7. For remaining pages, read only the latest Completed/report.
8. If no message/campaign was sent, ignore as neutral.
9. If the latest report contains `#2022`, pure or mixed with other codes, classify as a new restriction only when a restriction date can be extracted.
10. Apply to SB: `STATUS=Broadcast` + `RESTRICTED_UNTIL=<date from DTR>`.
11. Validate SB readback before alerting.
12. Alert channel `1522442220903337984` only after write + readback success.

## Required alert contents

The Discord alert must be readable by a human and explicitly state the side effect performed:

```text
Ação executada: Dash Smart Bidding atualizada automaticamente.
Campos aplicados: STATUS=Broadcast + RESTRICTED_UNTIL=data da DTR.
Validação: readback SB OK antes deste alerta.
```

Each row must include at minimum:

- page name
- large `FB_PAGE_ID` for opening `https://facebook.com/{FB_PAGE_ID}`
- small `PAGE_ID`
- bot user
- segurador/account
- DTR restriction date/time when available
- codes (`#2022`, plus any companion codes)

## Parser pitfall fixed

The DTR `#2022` text can appear in English or Portuguese. The parser must support both:

```text
You're temporarily restricted from messaging users until July 31 at 3:24 AM.
Você está com uma restrição temporária de enviar mensagens a usuários até 15 de julho às 23:08.
```

If `#2022` is present but the date is not parsed, do not write `RESTRICTED_UNTIL`; count/report as a parser/date extraction issue instead of silently treating it as done.

## Operational lesson

SB-only monitor output must be labelled as “registro SB” or “SB-only; DTR não lido”, never “nova página restrita”. The DTR cron is the operational source for new restriction alerts.