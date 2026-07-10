# Test template population from active linked templates — 2026-07-07

Session context: Rodolfo created one `Teste-<VERTICAL>-<Site>-<PageName>-<FB_PAGE_ID>-<PG>` Broadcast Template per vertical for Utility canary approval. Zeus populated those test templates with the 20 messages from active production templates of the same vertical.

## User-confirmed workflow

First step only:

1. For each test template, identify its vertical from the name, e.g. `US-CC-EN`.
2. Find an active/current Broadcast Template with `PAGES > 0` and the same vertical.
3. Prefer the same site/domain named in the test template when available, e.g. `Newsoun` test should copy from an active `Newsoun - US-CC-EN...` template.
4. Extract exactly the 20 current messages from the active source template.
5. Replace/delete whatever placeholder messages exist in the test template.
6. Install only those 20 source messages into the test template.
7. Do **not** run approvals yet unless Rodolfo explicitly says so.
8. Validate by live `/broadcast/Messenger` readback: target template exists and now has 20 messages matching the installed digest.

## Source selection pattern used

Map target → source by vertical, prefer same site, then highest linked pages.

Validated examples from this session:

```text
Teste-CA-CC-EN-Financeadx...     <- Financeadx - CA-CC-EN/EN-SR - g006-d Nicolas
Teste-DE-CC-DE-Newsoun...        <- Newsoun - DE-CC-DE/DE-SR - g005-d Kelly
Teste-GB-CC-EN-Zytiva...         <- Zytiva - GB-CC-EN/EN-SR - g003-d Isliago
Teste-ES-CC-ES-Openzed...        <- Openzed - ES-CC-ES/ES-ZW - AV - g003-d Isliago
Teste-MX-CC-ES-Financeadx...     <- Financeadx - MX-CC-ES/ES-ZW-SR - g006-d Nicolas
Teste-US-CAR-EN-Fincgriffin...   <- Fincgriffin - US-CAR-EN/EN - JBF - g001-d
Teste-US-CC-EN-Newsoun...        <- Newsoun - US-CC-EN/EN-SR - g005-d Kelly
Teste-US-CC-ES-Newsoun...        <- Newsoun - US-CC-ES/ES-ZW-SR - g005-d Kelly
Teste-US-JOB-ES-Spe...           <- Spe - US-JOB-ES/ES-ZW - AV - g006-d Nicolas
Teste-ZA-CC-EN-Financeadx...     <- Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas
Teste-AR-CC-ES-Financeadx...     <- Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas
```

## API implementation pattern

Use authenticated SB `/broadcast/Messenger` capture through headed/Xvfb session from the SmartBidding skill.

For each target:

1. Backup target row JSON before modification.
2. Backup source row JSON.
3. Parse source `MESSAGES` JSON.
4. Sort by `MESSAGE_ID` and take first 20.
5. Clean status fields before install (`APPROVED`, `INVALID_FORMAT`, `REJECTED`, `ERROR`, `REJECTED_REASON`) so the test template starts fresh.
6. Renumber `MESSAGE_ID` 1..20.
7. POST the complete target row payload back to `/broadcast/Messenger` with only `MESSAGES` replaced.
8. Fresh-read `/broadcast/Messenger` after all writes and verify:
   - template found;
   - `len(MESSAGES) == 20`;
   - digest of installed message text/CTA/link matches source digest.

## Guardrails

- Do not use this as a production rollout flow; it is for canary/test templates Rodolfo explicitly created.
- Do not run `Run Approvals` in this first population step unless explicitly requested.
- Do not copy from unlinked templates (`PAGES = 0`) unless no linked source exists and Rodolfo approves.
- Do not mix languages/countries even if the copy seems similar; vertical code in template name is the routing key.
- Preserve source message links/buttons during test-template population unless Rodolfo says to adapt links.
- Keep backups under `/root/mgs-agent/backups/sb-templates/` and report readback count/status, not raw API payloads.
