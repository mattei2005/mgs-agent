# OpenzedFinanzas native-copy probe across all campaigns — 2026-06-18

## Why this reference exists

Rodolfo explicitly corrected the workflow: for this Meta operation, **do not treat replacement as creating campaign/adset/ad from zero**. Buyers clone campaigns in Ads Manager; Ares must validate clone/copy semantics first. Creating from zero is not an acceptable proof path for this class of task.

He also clarified that campaigns can be `ACTIVE` or `PAUSED/OFF`; both must be visible and valid clone sources. `PAUSED` is not deleted.

## Read-only visibility confirmed

Account: `1356770869843984` (`OpenzedFinanzas-ES-CC-ES-03`)

Ares confirmed all 20 campaigns were readable via API. Each visible campaign had 2 adsets and 6 ads.

```text
Group             | Campaigns | Status mix     | Adsets/Ads each
------------------|-----------|----------------|----------------
Elena Santana     | 5         | ACTIVE         | 2 / 6
Patricia Flores   | 5         | PAUSED/OFF     | 2 / 6
Carla Rojas       | 5         | PAUSED/OFF     | 2 / 6
Gabriela López    | 5         | PAUSED/OFF     | 2 / 6
```

## Native copy probes performed

### Campaign-level deep copy across all 20 campaigns

Endpoint shape: `POST /<campaign_id>/copies` with `deep_copy=true`, `status_option=PAUSED`, rename suffix.

Result: failed on all 20 campaigns with the same Meta error family.

```text
Scope                    | Result
-------------------------|-----------------------------------------
20 readable campaigns     | all attempted
/campaign_id/copies deep  | failed on all 20
Repeated error            | code 100 / subcode 1885194
Full copy success         | none
```

Audit: `/root/mgs-agent/data/ares/meta-ads/audit/clone/campaign-deep-copy-any-20260618T222507Z.json`

### Campaign shallow copy + adset/ad native copy

A shallow `POST /<campaign_id>/copies` can create a paused campaign copy, but it contains no adsets/ads. Ares then tried adset-level native copy into the copied campaign using several parameter shapes.

```text
Step                               | Result
-----------------------------------|-----------------------------------------
/campaign_id/copies shallow         | OK, creates empty PAUSED campaign
/adset_id/copies campaign_id        | failed
/adset_id/copies + deep_copy        | failed
/adset_id/copies destination...     | failed
/ad_id/copies                       | not reachable without copied adset
```

Observed adset-copy errors:

```text
Variant                         | Error
--------------------------------|------------------------------
adset copy shallow              | code 100 / subcode 1885501
adset copy deep                 | code 100 / subcode 1885194
```

Audits:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/native-copy-knownids-elena-20260618T223952Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/adset-copy-param-probe-20260618T224018Z.json
```

All shallow/partial campaign copies were cleaned up and verified `DELETED` before reporting.

## Operational lesson

When Rodolfo says "clonar", do **not** summarize a fallback from-zero path as if it is operationally equivalent. The correct sequence is:

1. Verify token/account read-only.
2. Enumerate all campaign candidates, including `PAUSED`/OFF.
3. Try native copy paths across any viable source campaign if the goal is just to make one clone work.
4. Treat success only as a clone/copy that brings adsets/ads, not a campaign shell.
5. Delete/verify any empty or partial copy.
6. If public Graph copy endpoints fail on all candidates, ask for either:
   - the buyers' exact clone payload/script, or
   - permission to inspect the Ads Manager browser request that succeeds.

## Current blocker after this probe

Public Graph copy endpoints used by Ares can see all campaigns and can create campaign shells, but they do not reproduce the Ads Manager/buyer full clone. The missing piece is likely a specific Ads Manager/internal parameterization, async copy shape, or endpoint payload not captured by the simple public `deep_copy=true` flow.

Do not conclude that campaigns are invisible or deleted. Do not switch back to from-zero creation as the answer.
