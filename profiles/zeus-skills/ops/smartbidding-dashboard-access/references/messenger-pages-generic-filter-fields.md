# Messenger Pages — Generic Filter Fields and Restriction Caveat

Use this note when building advanced-search expressions in **Reports → Messenger Pages** (`/reports/messenger`).

## Broadcast metric identifiers

The visible Broadcast columns use these technical IDs in the generic filter:

```text
Visible label   Filter field
-------------   ----------------
SENDS           BD_SENDS
DELIVEREDS      BD_DELIVEREDS
%DELIVERED      BD_DELIVERED_RATE
```

For pages with at least one Broadcast send and zero Broadcast deliveries:

```text
BD_SENDS>0 BD_DELIVEREDS=0
```

The date is selected with the report date control; it is not part of this expression.

Do not substitute `SENDS>0 DELIVEREDS=0` when the intent is specifically the **Broadcast** group. `DELIVEREDS` exists as a separate Messenger metric, while the visible Broadcast `DELIVEREDS` column maps to `BD_DELIVEREDS`.

## Restriction exclusion cannot be expressed in this report alone

The Messenger Pages report dimensions exposed by the frontend include `DATE`, `COMPANY`, `DOMAIN`, `USER_LOGIN`, `PROFILE_NAME`, `PAGE_ID`, `USERNAME`, `PAGE_NAME`, `PAGE_START_DATE`, `STATUS`, `UTM_CAMPAIGN`, `SOURCE`, `COUNTRY`, `VERTICAL`, `LANGUAGE`, and `ACCOUNT_NAME`.

They do **not** include `RESTRICTED_UNTIL` or `NOTES/#2022`. Consequently:

- `NOT("Restricted")` does not reliably exclude restricted pages;
- filtering for `"Broadcast"` does not mean unrestricted, because an operationally restricted page can remain `STATUS=Broadcast` while `RESTRICTED_UNTIL` carries the restriction;
- to identify zero-delivery pages that are not already restricted, first filter with `BD_SENDS>0 BD_DELIVEREDS=0`, then reconcile the returned page IDs against **Accounts → Messenger → Page** or the authoritative restricted-page dataset.

## Verification source

When field names are uncertain, inspect the current frontend route chunk and its imported field definitions rather than guessing from visible labels. The route component imports separate dimension and metric field lists; the metric list is the authoritative mapping between visible labels and filter IDs for the deployed frontend. Re-check after a dashboard release because hashed asset names and available fields can change.
