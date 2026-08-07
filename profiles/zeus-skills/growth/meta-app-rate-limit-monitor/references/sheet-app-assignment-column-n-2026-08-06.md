# Meta App Assignment Column N Cutover — 2026-08-06

## Decision

Rodolfo superseded the Meta app assignment source in Sheet `1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY`, tab `Migracao 22/06` / gid `542936436`:

- column M / `NO APP` is historical;
- column N / `APP PROVISORIO` is the current app-routing truth for every app monitor;
- non-app status values in N are not app assignments and must be preserved fail-closed;
- column A / `Removidos acumulado` remains the X marker written by reconciliation.

## Sheet preflight

Canonical Service Account access passed on Drive and Sheets with project `mgs-core-prod` and `canEdit=true`. The tab had 232 data rows and 126 M→N differences.

Current N assignment distribution at cutover:

- B005-2: 135
- B006-2: 17
- B007: 21
- B013: 34
- non-app operational notes: 8
- blank N: 17

The retired/deleted apps B001, B002, B003, B004, B008, B009 and B010 had their operational assignments moved primarily to B005-2. Their API-health checks remain active, but they no longer own Sheet rows through historical M.

## Runtime changes

- `meta-app-roles-watch.sh` continues reading `A:Z`, now requires and selects `APP PROVISORIO` for every Sheet assignment/reconciliation path.
- `b013-dtr-link-watch.sh` expanded `A:M` to `A:N`, requires `APP PROVISORIO`, and selects only `APP PROVISORIO = B013`.
- Both scripts fail closed if required headers are missing.
- B013 live readback selected 34 N rows and reconciled 1 linked / 33 confirmed unlinked / 0 unknown with zero Sheet delta.

## B005-2 identity rendering incident and fix

B005-2 had 100 current Meta `/roles` entries. The old identity resolver sent all 100 IDs in one Graph multi-ID query; Meta returned HTTP 400, leaving every name unresolved and producing a malformed alert with numeric `SEGURADOR`/`PERFIL ID` plus `sem email`.

The resolver now uses bounded multi-ID chunks of at most 50 IDs, with bounded transient retry and user-token fallback. Production readback returned:

- two chunks;
- both HTTP 200;
- 100 requested / 100 resolved / 0 unresolved;
- corrected B005-2 live alert with zero `sem email` occurrences;
- 99 assigned Sheet identities currently present in Meta roles;
- 36 assigned B005-2 rows marked X (35 freshly absent plus one cumulative absence).

The nine-message malformed alert family was deleted after the corrected eight-message family was validated. Discord deletion hit four local HTTP 429 responses; all honored `retry_after` and succeeded within the bounded retry.

## Sheet safety

An all-numeric/unresolved role set now makes `role_identity_reconciliation.safe_for_sheet=false`, preserving existing X values rather than inventing mass removals. After chunked identity resolution, the full all-app dry run found:

- 173 checked app-intent rows;
- 137 present;
- 35 missing-current-Meta markers plus one cumulative marker;
- 8 non-app/unknown N rows preserved;
- 17 blank-N rows;
- zero pending Sheet updates after the live B005-2 reconciliation.

The seven deleted apps still return the known Meta OAuth `Application has been deleted` error. Their app-channel notification pause remains active until midnight ET, and N assigns no active app rows to them.

## Rollback

Backup: `/root/mgs-agent/backups/meta-app-sheet-column-n-20260806-211755`.

Rollback requires restoring both scripts and states together. Do not revert only one monitor, because mixed M/N ownership would create contradictory Sheet reconciliation.
