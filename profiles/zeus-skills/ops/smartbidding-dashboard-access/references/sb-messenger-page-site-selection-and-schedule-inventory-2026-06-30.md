# SB Messenger Page site selection + schedule inventory

Session: 2026-06-30. Context: Rodolfo asked Zeus to inspect Messenger Page broadcast schedules before reducing daily sends.

## Durable lesson

On `Accounts > Messenger > Page`, do not trust a partial selected-site count. A capture with only `Digital trust` selected showed 2,443 pages, but Rodolfo's UI showed 3,237 pages. The missing rows were from `Digital trust 2` publishers.

Correct validation for full MGS scope in this session:

```text
Selected sites: 56
Paginator: Showing 1 to 50 of 3237
Companies/groups: Digital trust + Digital trust 2
```

If the selector shows 45/48 sites or the paginator shows 2,443 rows, scope is incomplete.

## UI pitfall

Clicking/checking the `Digital trust 2` group row may visually check the group but not actually select all child publishers for the campaign/Page API refresh. The reliable route was:

1. Open the site multiselect on `Messenger > Page`.
2. Use the multiselect filter (`digital`) so both group blocks are visible.
3. Confirm/enable each `Digital trust 2` child publisher:
   - amazing
   - cliquet
   - Cliquetfinanzas
   - openzed
   - Openzedfinanzas
   - wantabrand
   - wantabrandfinance
   - wavesbee
   - Wavesbeefinanzas
   - zuout
   - Zuoutfinanzas
4. Close the multiselect.
5. Click the blue square refresh/update button next to the site selector — not the search button near the table filter.
6. Validate both: selector says `56 sites` and paginator says `Showing 1 to 50 of 3237`.

## API/data notes

The relevant response captured by the SPA is:

```text
GET https://api.jbfdigital.com.br/campaigns/Messenger?companies[]=...&source=Messenger
```

Rows include the page-level schedule fields needed for inventory:

```text
BROADCAST_TEMPLATE_NAME
BROADCAST_TIME
BROADCAST_CURRENT_MESSAGE_ID
BROADCAST_MESSAGE_ID
BROADCAST_LAST_SCHEDULE
RESTRICTED_UNTIL
PAGE_ID
COUNTRY
VERTICAL
COMPANY
```

Schedule times are page-level `BROADCAST_TIME`, not the template message body itself.

## Schedule inventory correction

With the incomplete 45-site scope, Zeus initially reported 2,443 pages. Corrected full-scope capture after selecting all 56 sites returned 3,237 pages. For the `09:00, 11:00, 14:00, 18:00, 20:00` schedule pattern, the same 5 templates remained, totaling 24 pages:

```text
2  AR  Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas
4  CA  Eggbev - US-CC-EN/EN-SR - g006-d Nicolas
12 CA  Financeadx - CA-CC-EN/EN-SR - g006-d Nicolas
2  US  Financeadx - MX-CC-ES/ES-ZW-SR - g006-d Nicolas
4  ZA  Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas
```

## Reporting standard

When reporting SB Page schedule inventories, include scope proof up front:

```text
Sites selecionados: 56
Páginas lidas: 3.237
Fonte: Accounts > Messenger > Page
Mudança: nenhuma
```

If the scope proof is missing, the inventory is not ready to trust.
