# DTR restriction expiry must clear SB NOTES codes — 2026-07-06

## Rodolfo correction

When a page leaves Messenger restriction, clearing `RESTRICTED_UNTIL` is not enough. The Smart Bidding `NOTES` field must also have stale restriction/error codes removed so humans do not keep reading the page as broken.

## Production rule

In `/root/mgs-agent/scripts/dtr-sb-page-health-sync.py`, when an active SB restriction is cleared because DTR latest Completed proves the page is no longer restricted:

- `status == SENT`:
  - set `RESTRICTED_UNTIL = null`;
  - remove transient delivery/error tokens from `NOTES`: `#2022`, `#10`, `#100`, `#551`, `TOKEN`, `APP_DELETED`, `PERMISSION`, `SEM_COMPLETED`;
  - preserve the human prefix/context in `NOTES` (site/segurador/language/owner text).

- latest DTR status is an error without `#2022`:
  - set `RESTRICTED_UNTIL = null`;
  - remove stale `#2022` from `NOTES`;
  - keep/add the current non-`#2022` error code because it is still the current DTR state.

## Implementation notes

Use exact token removal only. Do not blindly rewrite the whole notes string. Validate with SB readback: if `NOTES` is in payload, readback must exactly match the cleaned string before reporting success.

## Why

Rodolfo explicitly warned: “quando alguma pagina sair da restricao, precisa remover os codigos do notes, nao pode esquecer disso”. Stale `#2022` in `NOTES` after expiry creates false human interpretation that the page is still restricted.