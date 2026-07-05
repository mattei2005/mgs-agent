# DTR ↔ SB named-login scope correction — 2026-07-05

## Trigger

Rodolfo asked whether `disparosopenzedes@gmail.com` had divergence after a prior DTR↔SB audit report said it did not appear. He then provided screenshots proving:

- 1Password has item `Digitaltrchat - Disparos Openzed US-CC-ES` with username `disparosopenzedes@gmail.com`.
- SmartBidding `Accounts > Messenger > Page` shows rows for `LOGIN = disparosopenzedes@gmail.com` under `digital-trust-2` / `openzedfinanzas`.

## What went wrong

The prior bulk audit used active bot users from the live operational sheet as its DTR scope. `disparosopenzedes@gmail.com` was not in that 76-user active set, so it was excluded from both the DTR scan and the SB filtered comparison. Zeus incorrectly interpreted “not in audit JSON/CSV” as “no divergence.”

This is a scope error, not proof about the live dashboards.

## Correct rule

When Rodolfo names a specific login or provides screenshot evidence, revalidate that login directly even if the prior bulk audit omitted it.

Do not infer “no issue” from absence in a scoped audit unless the scope explicitly includes that login.

## Validation pattern

1. Confirm the 1Password item exists for the named login. Do not print credentials.
2. Collect live DTR pages for that exact credential.
3. Fetch live SB Messenger Page rows with full `digital-trust + digital-trust-2` publisher scope, not only active-sheet users.
4. Filter SB rows by the named `USER_LOGIN`.
5. Compare:
   - `FB_PAGE_ID` as primary stable identity;
   - `PAGE_ID`/PG small ID for migration/config divergence;
   - page name with Unicode normalization awareness;
   - DTR account/segurador vs SB `PROFILE_NAME`.
6. Report whether the login was excluded by the prior sheet scope.

## Session result for `disparosopenzedes@gmail.com`

Direct live validation found:

- DTR login OK.
- DTR accounts: 1.
- DTR pages: 12.
- SB rows for login: 12.
- OK: 1.
- Divergent: 11.
- DTR without SB: 0.
- SB without DTR: 0.

Main divergence: `FB_PAGE_ID` matched, but DTR small PG ID and DTR account/segurador differed from SB `PAGE_ID` and `PROFILE_NAME`.

Visible examples:

```text
Página              DTR PG   SB PAGE ID   DTR segurador       SB profile
-----------------   ------   ----------   -----------------   ----------------
Claudia Pacheco     22272    13972        Fernanda Peixoto    Jamille Rodegheri
Sara Ramírez        22267    22073        Fernanda Peixoto    Jamille Rodegheri
Ana Pacheco         22266    22072        Fernanda Peixoto    Jamille Rodegheri
Daniela Pacheco     22263    22071        Fernanda Peixoto    Jamille Rodegheri
Rosa Montoya        22262    22070        Fernanda Peixoto    Jamille Rodegheri
```

`Luisa Gallardo` matched (`PAGE_ID = 22273`, `FB_PAGE_ID = 684845951388882`, `PROFILE_NAME = Fernanda Peixoto`).

## Durable lesson

Bulk audit scope and named-login truth are different layers. If the user challenges a missing login with evidence, treat it as a scope-discovery bug and run a targeted live check before answering.