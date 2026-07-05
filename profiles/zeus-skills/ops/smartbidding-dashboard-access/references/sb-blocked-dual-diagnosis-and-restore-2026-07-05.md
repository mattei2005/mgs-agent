# SB Messenger `Blocked` rows — dual diagnosis before reactivation

Session: 2026-07-05  
Scope: DTR → SmartBidding page-health sync, FINANCETOPFEED / segurador Barbara Cristina.

## Durable lesson

`STATUS=Blocked` in SmartBidding is not a root-cause diagnosis. It is only an operational state.

Before changing a Messenger Page row from `Blocked` back to `Broadcast`, diagnose two separate layers:

1. **Public page availability** — whether `https://facebook.com/{FB_PAGE_ID}` opens publicly.
2. **Operational access through the segurador/profile** — whether MGS still has access to the page through the Facebook profile/segurador connected in DTR/Facebook context.

A public Facebook URL opening normally is **not sufficient** to reactivate the row. It only proves the page may still be online. The segurador/profile may have fallen, causing MGS to lose access to otherwise-online pages.

## Correct classification

- **Page blocked/down**: public page/access fails. Keep `Blocked`.
- **Segurador/profile fallen**: page is public, but MGS lost operational access through the profile/segurador. Keep `Blocked` until profile access is restored or the page is moved to a working segurador.
- **False blocked / access restored**: only reactivate after both page availability and operational segurador/profile access are validated.

## Pitfall observed

Zeus incorrectly reactivated 7 FINANCETOPFEED rows from `Blocked` to `Broadcast` because the public Facebook URLs opened. Rodolfo corrected that these rows were blocked because the segurador/profile fell, so MGS no longer had page access even though pages could still be online.

Corrective action was to restore all 7 rows to `Blocked` and patch the script/skill rule so future apply jobs do not perform `Blocked → Broadcast` from URL availability alone.

## Implementation rule for automation

In DTR/SB sync scripts:

- For `sb_status == 'Blocked'`, do not add `STATUS='Broadcast'` based only on `fb_page_opens() == 'available'`.
- Append/report an observation such as `blocked_requires_page_and_segurador_diagnosis`.
- Treat blocked rows as a manual/diagnostic queue unless a validated routine can prove both:
  - page public availability; and
  - operational access through the active segurador/profile.

## Reporting rule

When reporting `Blocked` rows, say what was actually validated:

- `URL pública abre` = page appears publicly available.
- `Acesso segurador validado` = MGS operational access was confirmed.
- If only the URL was checked, label the case as incomplete diagnosis; do not call it safe to reactivate.
