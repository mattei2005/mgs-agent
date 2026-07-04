# SB pending-template schedule rollout — local-country hours to Brazil time (2026-07-02)

## Context

Rodolfo asked to update the Messenger Page `BROADCAST_TIME` for templates that had not yet been migrated/reduced for Utility Template operations. Desired send hours were given as local-country hours:

```text
07:00, 08:00, 10:00, 11:00, 13:00, 15:00, 18:00, 20:00
```

SB/Dash stores `BROADCAST_TIME` in `America/Sao_Paulo`, so schedules must be converted before writing.

## Canonical timezone map from Rodolfo

```text
US -> America/New_York
CA -> America/Toronto
MX -> America/Mexico_City
AR -> America/Sao_Paulo + America/Santiago
DE -> Europe/Berlin
ES -> Europe/Paris + Europe/Rome
GB -> Europe/London
ZA -> Africa/Johannesburg
FR -> Europe/Paris
```

For this session, the actionable countries were AR, CA, DE, MX, US, ZA. TR was listed in pending templates but had no Page rows in the validated snapshot.

## Conversion used for July 2026

```text
AR-CC-ES  -> 07,08,10,11,13,15,18,20
CA-CC-EN  -> 08,09,11,12,14,16,19,21
DE-CC-DE  -> 02,03,05,06,08,10,13,15
MX-CC-ES  -> 10,11,13,14,16,18,21,23
US-*      -> 08,09,11,12,14,16,19,21
ZA-CC-EN  -> 02,03,05,06,08,10,13,15
```

## Critical pitfall: use template country, not Page row COUNTRY

Some Page rows had a `COUNTRY` that did not match the template country, for example:

- DE template rows with `COUNTRY=US`
- MX template rows with `COUNTRY=US`

The correct schedule conversion for this task was based on the country embedded in `BROADCAST_TEMPLATE_NAME` / vertical (`DE-CC-DE`, `MX-CC-ES`, etc.), not the Page row `COUNTRY` field. Using page `COUNTRY` caused a wrong first pass where a subset of DE/MX rows got US-converted hours. The fix was to derive country from the template name first and fall back to row `COUNTRY` only if parsing fails.

Recommended helper:

```python
def template_country(name):
    m = re.search(r'([A-Z]{2})-[A-Z-]+-[A-Z]{2}(?=/)', name or '')
    if m:
        return m.group(1)
    m = re.search(r'([A-Z]{2})-[A-Z-]+-[A-Z]{2}', name or '')
    return m.group(1) if m else None
```

## Validation pattern that worked

The full 56-site Page capture can intermittently return only the 45-site / 2,443-row scope even when the operation target rows are present. For this rollout:

- last validated full snapshot had 3,237 rows;
- live response exposed 2,443 rows;
- all 403 target Page rows were still present in the live response;
- validation was done by filtering the live response by target row IDs and checking `BROADCAST_TIME` exactly.

Avoid validating hundreds of rows by `GET /campaigns/Messenger/{ID}` one-by-one; the endpoint timed out during validation. Prefer one live `/campaigns/Messenger` response filtered by intended IDs when it contains all target rows.

## Result shape

Final validated result:

```text
26 templates requested
18 templates had active Page rows
403 Page rows updated
6 update-many batches
0 validation failures
```

Templates without active Page rows were not changed and should be reported separately.

## Operational rule

For future schedule updates by country/vertical:

1. Parse target country from `BROADCAST_TEMPLATE_NAME` / vertical.
2. Convert Rodolfo's desired local hours to `America/Sao_Paulo` using the canonical timezone map.
3. Backup target Page rows before writing.
4. `PUT /campaigns/Messenger/update-many` grouped by identical converted time list.
5. Validate target row IDs from a live Page response; assert exact `BROADCAST_TIME` and report no-row templates separately.
