# OpenzedFinanzas — EU DSA adset diagnostic (2026-06-19)

## Context

During a controlled Patricia Flores clone-source execution, `POST /adsets` failed repeatedly with:

```text
code: 100
subcode: 1487202
message: Invalid parameter
error_user_msg/title: null
```

The same subcode appeared both on manual `POST /adsets` and earlier native copy probes. A test posting the same adset payload into the original source campaign also failed, proving the failure was not only caused by the newly-created campaign's bad `start_time`.

## Durable lesson

For Europe/UE financial campaigns, especially `FINANCIAL_PRODUCTS_SERVICES`, do not treat adsets like North America campaign structures. Before any write, explicitly introspect compliance fields. The Graph default response hides important fields.

Required GET fields on source adsets include:

```text
dsa_beneficiary
dsa_payor
optimization_goal
billing_event
destination_type
promoted_object
targeting
attribution_spec
optimization_sub_event
is_dynamic_creative
use_new_app_click
start_time
```

Also search field names containing: `dsa`, `beneficiary`, `payor`, `regulated`.

## Source values observed

GET confirmed Patricia's real adsets expose DSA fields:

```text
Adset ID             | Name                  | Page ID          | dsa_beneficiary | dsa_payor
---------------------|-----------------------|------------------|-----------------|----------
120248290297260604   | Conjunto 02 - IMAGENS | 1063171606876651 | Openzed         | Openzed
120248290297250604   | Conjunto 01 - VÍDEOS  | 1063171606876651 | Openzed         | Openzed
```

A related/source adset `120247501687700604` also returned:

```text
dsa_beneficiary = Openzed
dsa_payor       = Openzed
page_id         = 1037297262803284
```

Important: Rodolfo had seen UI wording suggesting `Beneficiary & Payer: Digital Trust`, but the API source strings were `Openzed`. Always use exact API-returned source values when cloning, including capitalization/accenting.

## Payload correction attempted

The first adset payload was updated with source-matched writable fields:

```json
{
  "attribution_spec": [
    {"event_type": "CLICK_THROUGH", "window_days": 7},
    {"event_type": "VIEW_THROUGH", "window_days": 1}
  ],
  "optimization_sub_event": "NONE",
  "is_dynamic_creative": false,
  "use_new_app_click": false,
  "dsa_beneficiary": "Openzed",
  "dsa_payor": "Openzed",
  "status": "PAUSED",
  "start_time": "2026-06-19T23:00:00Z"
}
```

Even after adding DSA, Meta still returned `100/1487202`, with no `error_user_msg` or `error_user_title`.

## Diff discipline required

Before future write attempts, do a complete source-vs-payload diff at all three levels:

1. Campaign source vs campaign payload.
2. Adset source vs adset payload.
3. Source ads/creatives vs rebuilt ad/adcreative payloads.

Classify each field:

```text
IGUAL
SÓ NA SOURCE
VALOR DIFERENTE
READ-ONLY/derivado
```

Prioritize `SÓ NA SOURCE` and `VALOR DIFERENTE` fields that are likely writable.

## Additional candidates found after DSA

At the adset level, after adding DSA, only expected differences remained:

```text
name        | RPL naming difference
start_time  | new scheduled start
status      | PAUSED by safety
```

At the ad level, source ads had writable-looking fields absent from rebuilt ad payloads:

```text
tracking_specs
conversion_specs
```

These do not explain an adset creation failure, but they are likely needed later for `/ads` parity.

## Start time lesson

A campaign created with local offset string `2026-06-20T01:00:00+0200` returned epoch-like `1970-01-01T00:59:59+0100` on GET. Use UTC Z strings for new scheduled starts, computed via real `Europe/Madrid` timezone (DST-aware), e.g.:

```text
2026-06-20 01:00 Madrid -> 2026-06-19T23:00:00Z
```

Do not use a fixed offset; December differs from June.

## Audit files

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-source-dry-run-patricia-1-20260618T224851Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/controlled-exec-patricia-1-20260618T225310Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/adset-1487202-diff-patricia-img.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/source-total-diff-dsa-diagnostic.json
```

## Communication lesson

Rodolfo corrected the workflow: do not say fields were "not found" or retry blind payload variations. For regulated EU ads, identify all explicit source fields first, produce a structured diff, then write one object at a time with GET validation and stop at each checkpoint.
