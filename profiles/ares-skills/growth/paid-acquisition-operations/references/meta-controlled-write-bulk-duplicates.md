# Meta Ads controlled-write: bulk duplicates and scheduled campaign normalization

Use this reference when Rodolfo approves a concrete Meta Ads write such as creating scheduled duplicates, changing budgets, removing bid caps, or normalizing campaign/adset/ad structure.

## Durable lessons from Elena/OpenzedFinanzas

1. **Validate the live target before creating more objects.**
   - If the user says “deixar 20 campanhas”, first count the current non-deleted in-scope campaigns by API.
   - Compute `needed = target_count - current_count`.
   - If `needed <= 0`, do not create duplicates; validate whether the existing campaigns already meet the structure/budget/start requirements.

2. **For “no bid cap”, set strategy at campaign level and omit adset bid.**
   - Known-good pattern:
     - campaign: `bid_strategy=LOWEST_COST_WITHOUT_CAP`
     - adset: omit `bid_amount`
     - adset: do not set `COST_CAP`
   - Setting/removing bid cap only at adset level can fail with Meta `code=100`, `subcode=1815857`.

3. **Campaign edge may not be enough to build templates.**
   - Some campaigns may not return usable adsets through the direct campaign edge in every context.
   - Robust template discovery: fetch account-level adsets and ads, then group by `campaign_id` / `adset_id` locally.

4. **When duplicating legacy creatives, prefer reusing `creative_id` for functional duplicates.**
   - Reusing existing `creative_id` avoids triggering raw creative deep-copy failures around legacy `standard_enhancements`.
   - This is a functional duplicate pattern, not proof of “perfect clone” attribution preservation.

5. **After any long/background write, re-open the audit and verify live state by GET.**
   - Do not trust `exit_code=0` alone.
   - Verify: campaign count, status/effective_status, daily_budget, start_time range, adset count, ad count, and absence of `bid_amount` when bid cap removal was requested.

6. **If the script overshoots the target, clean up immediately with audit.**
   - Delete only the known extra campaign IDs from the creation audit.
   - Verify each extra campaign returns `effective_status=DELETED`.
   - Recount final in-scope campaigns and validate requirements again.

## Minimum audit fields

```text
source_audit
created/deleted campaign IDs
target_count
current_count_before
needed_to_create
final_count_after
budget_minor_units
start_time range
adset_count per campaign
ad_count per campaign
bid_amount presence/absence
GET verification timestamp
errors/cleanup results
```

## Reporting pattern

Report the final live state, not the microsteps:

```text
Estado final

Item                  | Resultado
----------------------|-------------------------------
Campanhas finais      | 20
Status                | ACTIVE
Budget                | USD 25 cada
Start programado      | 00:01 até 00:20 Europe/Madrid
Estrutura             | 1 conjunto / 3 anúncios
Bid cap               | sem bid_amount nos conjuntos
Problemas encontrados | 0
Validação             | GET Meta pós-ação
```
