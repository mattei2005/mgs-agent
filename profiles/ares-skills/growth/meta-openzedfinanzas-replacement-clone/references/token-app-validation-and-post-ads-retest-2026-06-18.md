# OpenzedFinanzas clone — token/app validation and POST /ads retest

Session learning from 2026-06-18 retests after Rodolfo changed/migrated VPS.

## Why this matters

When clone attempts fail, do not assume VPS/IP migration fixed or caused the Meta API issue. Validate the API layers in order and separate:

1. Token/app validity.
2. Read access to source campaign/adset.
3. Campaign creation.
4. Adset creation.
5. Creative creation.
6. Final `POST /ads`.

## Observed states

Earlier token/app state:

```text
Layer                    | Result
-------------------------|---------------------------------------------
GET source campaign       | OK
Create campaign           | OK
Create adset              | OK
Create adcreative video_id | OK
POST /ads                 | blocked: code 31 / subcode 3858385
```

After token/app update, the retest failed earlier:

```text
Layer              | Result
-------------------|---------------------------------------------
Token 1Password     | read OK, field `credential`, len only
GET source campaign | blocked: code 190
Meta message        | Error validating application. Application has been deleted.
Objects created     | none
```

Do not print token values; report only item, field, len, status, and sanitized Meta error.

## Focused retest pattern

If the full clone script is slow because another Meta cron is backing off/rate-limited, use a minimal probe that does not use the bounded backoff wrapper:

1. Read token from 1Password.
2. `GET /<source_campaign_id>` with safe fields.
3. If GET fails with `code=190`, stop: app/token invalid, do not try writes.
4. If GET succeeds, create a PAUSED temporary campaign and PAUSED adset.
5. Test `POST /ads` using an existing source `creative_id` to isolate the final layer.
6. Always delete/verify the temporary campaign if created.
7. Save audit JSON under `data/ares/meta-ads/audit/clone/`.

This is a diagnostic probe only; the production replacement path still requires exactly 3 ads and full validation before keeping the campaign.

## Interpretation

- `code=31 / subcode=3858385` at `POST /ads`: account/user/app is blocked by pending authentication for ad creation/modification; creative route may still be correct.
- `code=190` with `Error validating application. Application has been deleted.` at first GET: token belongs to a deleted/invalid Meta app. Fix token/app first; VPS/IP changes are not the active blocker.
