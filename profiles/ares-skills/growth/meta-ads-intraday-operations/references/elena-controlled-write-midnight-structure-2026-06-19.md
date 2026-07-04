# Elena controlled-write midnight structure adjustment — 2026-06-19

## Trigger

Rodolfo moved from pure read-only calibration to a specific, explicitly approved controlled-write maintenance request for the current Elena Santana campaigns at account midnight.

Approved request:

```text
1. At account-day rollover, active campaigns should no longer run USD 100/day each.
2. Use only current Elena campaigns, not Patricia/other paused pages, after clarification.
3. Each campaign should become: campaign + 1 adset + 3 ads.
4. Disable Meta Ads automated rules that pause ads/campaigns.
5. Remove USD 2 bid cap at adset level so Meta can deliver normally.
6. Add Geizian/gestors/Isliago to logs-aquisicao; if Ares lacks Discord admin token, hand off to Zeus/admin.
```

## Correct workflow for similar requests

1. Treat this as **explicit controlled-write authorization** for the named scope only. Do not generalize to full autonomy.
2. Load Meta guardrails/intraday skill and inspect operation config first.
3. Verify live account state before planning:
   - active campaigns;
   - campaign budgets;
   - adsets per campaign;
   - ads per adset;
   - bid caps / bid strategy;
   - automated Meta rules.
4. If the user's requested count does not match live state, clarify the scope before writing.
   - In this session the user said “20 campaigns”, but live state showed only 5 active Elena campaigns.
   - Clarified decision: use only current Elena active campaigns: 5 campaigns at USD 25 each.
5. Disable Meta automated PAUSE rules immediately if explicitly requested, and verify each by GET.
6. For rollover changes, create a script + profile wrapper and schedule a one-shot Hermes cron at account midnight.
7. Dry-run the script before scheduling. The dry-run must output selected campaign/adset plan and audit path.
8. The scheduled script must:
   - never print tokens;
   - write audit JSON;
   - validate after each write with GET;
   - print a compact sanitized summary to logs-aquisicao.
9. Report infra because scripts/cron/data changed.
10. If Discord channel permission changes are requested but Ares lacks a Discord admin token/capability, send an explicit handoff/request to Zeus/admin with user IDs and channel ID; do not pretend it was done.

## Implementation pattern used

Script created:

```text
/root/mgs-agent/scripts/ares-meta-elena-midnight-structure-adjust.py
/root/.hermes/profiles/ares/scripts/ares-meta-elena-midnight-structure-adjust.sh
```

One-shot cron:

```text
Name: Ares Elena midnight structure adjust - approved write
Schedule used: 2026-06-19T18:00:00 America/New_York = 2026-06-20 00:00 Europe/Madrid
Deliver: logs-aquisicao
Mode: no_agent=true script-only
```

Dry-run audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/controlled-write/elena-midnight-structure-adjust-20260619T185020Z.json
```

## Meta rule handling

Rules discovered on `act_1356770869843984/adrules_library`:

```text
Rule ID            | Name
-------------------|----------------------------------
1706384407070888   | DESATIVAR ANÚNCIOS SEM RESULTADOS
1142483632283037   | DESATIVAR ANÚNCIOS RUINS
```

Both were `ENABLED` and had `execution_type=PAUSE`. They were disabled with POST `status=DISABLED` and verified by GET.

## Scope pitfall

Do not infer “20 campaigns” means reactivating Patricia/Carla/Gabriela or cloning new campaigns. When live state contradicts the request, clarify. Rodolfo chose current Elena only.

Final scoped targets:

```text
Elena Santana - ES - ESP - (pg_22091) - 1
Elena Santana - ES - ESP - (pg_22091) - 2
Elena Santana - ES - ESP - (pg_22091) - 3
Elena Santana - ES - ESP - (pg_22091) - 4
Elena Santana - ES - ESP - (pg_22091) - 5
```

## Discord permission pitfall

Ares may not have a usable Discord admin token in its environment. For channel membership/permission updates, first try only if a valid admin path is available. If not, send a Zeus/admin handoff with:

```text
channel name + channel ID
requested users + IDs
reason/context
```

Do not report Discord permissions as completed unless API write succeeds or Zeus/admin confirms.
