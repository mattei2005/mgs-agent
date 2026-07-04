# Perfect clone attribution 7/1 investigation — 2026-06-19

## Trigger

Rodolfo rejected the statement that the Elena clone divergence was acceptable:

> “isso eh inadimissivel!! tem q ser 100% clone perfeito”

Operational rule: if the user asks for clone perfeito / “do jeitinho que é”, do **not** call a clone successful/perfect if any source field such as attribution differs. A structurally complete clone with attribution changed from `7-day click + 1-day view` to `1-day click` is only a functional/test clone, not a perfect clone.

## Source vs clone issue

Source campaign:

```text
Elena Santana - ES - ESP - (pg_22091) - 4
Campaign ID: 120248940367540604
```

Source adsets use:

```text
attribution_spec = 7-day click + 1-day view
```

Manual rebuild clone created 2 adsets + 6 ads, but adsets were forced to:

```text
attribution_spec = 1-day click
```

That divergence is unacceptable for clone perfeito.

## Tests performed

### 1. Update cloned adsets back to 7/1

Target cloned adsets:

```text
120248959249340604
120248959251300604
```

Result: failed.

```text
code/subcode | 1 / 1504040
Title        | Ya no se admite la modificación del intervalo de atribución
Message      | Ya no es posible actualizar el intervalo de atribución después de crear un conjunto de anuncios. En su lugar, crea un nuevo conjunto de anuncios.
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-fix-attribution-7-1-update-20260619T063000Z.json
```

Lesson: attribution cannot be fixed after adset creation. If an adset is created with wrong attribution, discard/recreate; do not attempt update as a recovery path.

### 2. Source vs clone diff

Diff confirmed that outside IDs/status/dates/read-only fields, the relevant difference was attribution/lineage:

```text
attribution_spec
source_adset/source_adset_id lineage
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adset-source-vs-clone-7-1-diff-20260619T070500Z.json
```

### 3. Native campaign deep copy

Regular `/campaign_id/copies` with `deep_copy=true` failed:

```text
code/subcode | 100 / 1885194
Title        | La solicitud de objetos para copiar es demasiado grande
Message      | total ads/adsets/campaigns to copy must be < 3; use asynchronous batch requests for more objects
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-native-deep-copy-token2-7-1-probe-20260619T063500Z.json
```

### 4. Native adset copy

`/adset_id/copies` failed with attribution validation:

```text
code/subcode | 100 / 1885501
Message      | accepted click/view values are (1,0)
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-native-adset-copy-7-1-probe-20260619T064000Z.json
```

### 5. Manual create with `source_adset_id`

Adding `source_adset_id` to adset create did not preserve lineage and failed with the same attribution error:

```text
code/subcode | 100 / 1885501
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-create-adset-with-source-adset-id-7-1-20260619T071000Z.json
```

### 6. Async batch/native copy attempts

Meta’s error says async batch is needed for >3 objects, but first schema attempts failed:

```text
Single request adbatch          | code 194, adbatch too few elements
With method key                 | code 100, invalid key method in adbatch[0]
relative_url with API version   | code 2500 unknown path components
relative_url no version         | code 1815379 invalid relative_url
```

Audits:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-async-batch-native-copy-7-1-20260619T064500Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-async-batch-native-copy-2req-7-1-20260619T065000Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-async-batch-native-copy-2req-nomethod-7-1-20260619T065500Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-async-batch-native-copy-relative-noversion-20260619T070000Z.json
```

## Current root-cause hypothesis

Manual rebuild via public `/campaigns` + `/adsets` is revalidating current Messenger/offsite conversion attribution rules and accepts only `(1,0)`. The source likely retains `7-day click + 1-day view` due to internal Ads Manager lineage/legacy duplication context. Source fields such as `source_adset_id` are read-only or non-effective for preserving this lineage via manual create.

## Operational rules added

1. Do not describe a clone as “perfect” unless all user-critical fields match, including attribution.
2. If source uses 7/1 and clone uses 1-click, label it “functional clone/test clone”, not full/perfect clone.
3. Never accept attribution divergence as “inevitable” without first trying corrective paths and reporting exact Meta blockers.
4. Updating attribution after creation is not a recovery path (`1504040`); recreate or discard.
5. For perfect clone with 7/1, prioritize true native/async copy or Ads Manager UI duplicate; manual rebuild is currently not a perfect-clone path.
6. If native copy says object count too large (`1885194`), continue investigating Meta async batch schema or use UI duplicate as practical fallback.

## Next investigation path

- Continue with Meta async batch request schema specifically for native `/copies`, or reproduce via Ads Manager UI duplicate and inspect resulting API objects.
- If UI duplicate preserves 7/1, compare copied adsets against manual clone to identify hidden lineage/context fields not accepted by public create.
- If async/native API remains blocked for app/tier, report that perfect 7/1 clone requires UI duplicate or a higher/Ads Manager internal copy path.
