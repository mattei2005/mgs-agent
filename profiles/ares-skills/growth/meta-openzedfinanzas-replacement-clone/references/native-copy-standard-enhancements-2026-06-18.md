# OpenzedFinanzas clone — native copy vs create-from-zero (2026-06-18)

## User correction

Rodolfo corrected the workflow: for this operation, do **not** treat replacement as creating a campaign/adset/ad from zero. His media buyers clone campaigns; the API path should prioritize Meta native copy/clone semantics. Creation from zero may only work under a different System User context and is not the expected route for this token/user flow.

## What was tested

Account: `1356770869843984` (`OpenzedFinanzas-ES-CC-ES-03`)

Alternative source page/campaign group tested:

```text
Group             | Page ID          | Example source campaign
------------------|------------------|------------------------
Elena Santana     | 990898360783030  | 120248940367540604
Patricia Flores   | 1063171606876651 | 120248290564280604
Carla Rojas       | 1037297262803284 | 120247501687810604
Gabriela López    | 1097045910150412 | 120246399685010604
```

## Observed clone behavior

```text
Path / method                                  | Result
-----------------------------------------------|------------------------------------------------------------
`/<campaign_id>/copies` without `deep_copy`     | Creates only a shallow empty campaign copy; no adsets/ads.
`/<campaign_id>/copies` with `deep_copy=true`   | Fails with copy request too large: total copied objects must be < 3.
`/<adset_id>/copies` sync with deep copy         | Use async batch for adsets with ads; sync path not enough.
Async batch `POST <adset_id>/copies deep_copy`  | Runs, but session FAILED due obsolete standard enhancements.
Manual campaign+adset + `/<ad_id>/copies`       | Ad copy fails with subcode `3858504`.
Manual campaign+adset+creative+ad create        | Reaches `POST /ads`, then account pending action may block.
```

Important cleanup validated: shallow/partial copy campaigns were marked `DELETED` and verified via GET before reporting.

## Key durable Meta error

Native clone failure from async session:

```text
status        | FAILED
code          | 100
subcode       | 3858504
user title    | El anuncio no debe incluir mejoras estándar
meaning       | The source ad/creative carries legacy `standard_enhancements`; Meta copy path rejects it.
```

Meta message indicated the old standard enhancements field is deprecated and individual creative features must be set instead.

## Operational rule for future clone attempts

1. Start with native copy/clone semantics, not from-zero creation.
2. If copying full campaign with `deep_copy=true` fails as too large, do not conclude cloning is impossible; switch to adset-level async copy or by-parts native copy.
3. For source ads carrying legacy `standard_enhancements`, the next implementation must clone while suppressing/normalizing those creative features. Do not keep retrying the same `/<ad_id>/copies` or adset `deep_copy` call without changing this part.
4. If using manual creative rebuild as fallback, treat it as a workaround only after native clone paths are exhausted; preserve PAUSED status and exact cleanup.
5. Never leave shallow empty campaign copies alive; verify adsets/ads count and delete if not exact.

## Next implementation direction

Build a clone path that either:

- uses Meta native copy endpoints with an override/rename/body option that prevents deprecated `standard_enhancements` from being copied; or
- copies campaign/adset natively, then rebuilds ads from source creative assets with `degrees_of_freedom_spec` using individual feature opt-outs instead of the legacy field, while avoiding full from-zero campaign semantics where possible.

Before declaring success, verify with GET:

```text
Campaign status      | PAUSED
Daily budget         | 2500 (USD 25)
Adsets               | exact expected count
Ads                  | exact expected count (usually 3 for replacement test)
Partial objects      | none left active if failed
```
