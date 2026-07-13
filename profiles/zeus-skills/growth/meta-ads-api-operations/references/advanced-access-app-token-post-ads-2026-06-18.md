# Advanced Access app/token did not clear POST /ads checkpoint — 2026-06-18

## Context

Rodolfo swapped the Meta app and updated the token in 1Password. The new app reportedly had Advanced Access for all required permissions. The goal was to retest whether the previous `POST /ads` checkpoint was caused by app permission/access level rather than VPS/IP/environment reputation.

## Controlled retest shape

- Host: current MGS VPS on Hetzner/Ashburn, no proxy
- Graph version: `v25.0`
- Script: `/root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py`
- Source/loser campaign: `120248290564280604`
- Budget guardrail: `$25/day`
- Creative mode: `video_data_minimal`
- Token source: 1Password, field `credential`
- Token length observed: `198`
- Credentials were not printed or exposed

## Results

Dry-run succeeded and selected the same class of winners/assets.

Controlled write result:

```text
Step                         Result
---------------------------  --------------------------------------------
Create campaign PAUSED       OK
Create adset PAUSED          OK
Create adcreative video_id   OK
Create ad / POST /ads        Failed
Meta error                   code=31 / subcode=3858385
User-facing title            Autentica tu cuenta
Cleanup                      OK — partial campaign set DELETED and verified
Partial campaign             120248930613700604 → DELETED
```

The failure remained endpoint-specific: campaign, adset, and adcreative writes succeeded; only `POST /ads` failed.

## Diagnostic conclusion

Changing to an app/token with Advanced Access did **not** resolve the `POST /ads` checkpoint. This weakens the hypothesis that the failure is ordinary app permissioning or missing Advanced Access.

The stronger remaining hypotheses are:

1. Host/IP/datacenter/fingerprint reputation from the current Hetzner VPS.
2. Meta checkpoint/trust state specifically triggered by API-side ad creation/modification.
3. Difference between browser/Ads Manager session flow and Marketing API `POST /ads` flow.

## Next decisive test

Run the same script, token, payload, source campaign, Graph version, and budget guardrail from Hostinger (or another known-success host) while changing only the host/IP/datacenter. If it passes outside Hetzner, treat Hetzner/VPS environment as the operational blocker for this flow. If it fails identically, return to token/profile/API-flow diagnostics.