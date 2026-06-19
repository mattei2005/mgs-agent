# Elena pragmatic resolution probe — 2026-06-19

Session purpose: Rodolfo asked to stop debating the ideal clone model and resolve the Meta creation path pragmatically. This was still a diagnostic/test path, not a permanent replacement for the official Ares 1x3 standard.

## Key outcome

```text
Layer                         | Result
------------------------------|------------------------------------------------------------
Campaign creation              | Works with Elena fields, PAUSED, USD 25
Campaign native shallow copy    | Works but still returns campaign start_time=1970
Adset with source attribution 7/1 | Fails with Meta 1885501 saying allowed attribution is (1,0)
Adset with 1-day click / no view | Works; first adset created PAUSED and validated
Ad creation using existing creative | Blocked by Meta pending account authentication
Cleanup                         | Partial campaign deleted and verified
```

## Practical payload that passed for the first Elena adset

```json
{
  "status": "PAUSED",
  "billing_event": "IMPRESSIONS",
  "optimization_goal": "OFFSITE_CONVERSIONS",
  "optimization_sub_event": "NONE",
  "destination_type": "MESSENGER",
  "promoted_object": {
    "pixel_id": "629060785934493",
    "custom_event_type": "COMPLETE_REGISTRATION",
    "page_id": "990898360783030",
    "smart_pse_enabled": false
  },
  "attribution_spec": [
    {"event_type": "CLICK_THROUGH", "window_days": 1}
  ],
  "bid_amount": 200,
  "is_dynamic_creative": false,
  "use_new_app_click": false,
  "dsa_beneficiary": "Openzed",
  "dsa_payor": "Openzed",
  "regional_regulated_categories": ["SPAIN_FINSERV", "VOLUNTARY_VERIFICATION"]
}
```

Targeting matched source: ES, age 18–65, home/recent, relaxed brand safety, `targeting_automation.advantage_audience=1`.

## Important interpretation

The source UI/API showed 7-day click + 1-day view, but Meta refused that attribution in the new campaign/adset creation context and explicitly required `(1,0)`. For this pragmatic diagnostic path, using `1-day click / 0-view` is an acceptable **test workaround** to prove the adset layer can be created. Do not silently treat it as faithful clone parity or update the official Ares standard without Rodolfo's explicit decision.

## Final blocker

`POST /ads` returned:

```text
code           | 31
subcode        | 3858385
title          | Autentica tu cuenta
message        | This request requires the user to take a pending action
```

Literal Spanish user message said the account cannot create or modify ads until authenticated in Ads Manager. Current ads continue running normally.

This is not a DSA/adset payload problem. It is the final ads-layer security checkpoint for the user/account/app.

## Audit files

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-resolve-native-parent-probe-20260619T041500Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-resolve-adset-1click-20260619T042000Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-resolve-create-3ads-existing-creatives-20260619T043000Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-resolve-cleanup-20260619T043500Z.json
```

## Procedure to reuse

1. For Elena/page `pg_22091`, if goal is just to prove API write path, create campaign PAUSED with USD 25 and finance ES fields.
2. Create first adset PAUSED using the compliance package and `attribution_spec=[CLICK_THROUGH 1]`.
3. Validate via GET.
4. Attempt ads only after Ads Manager pending authentication is cleared.
5. If ads still fail with `31/3858385`, stop; do not keep mutating creative/adset fields.
6. Delete/verify partial campaign when the diagnostic path is done or blocked.
