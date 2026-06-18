# OpenzedFinanzas clone — retest on alternate page and omit Instagram

Session learning from 2026-06-18 after Rodolfo asked whether Ares could try another page/campaign inside the ad account.

## Account page/campaign map observed

Read-only map from the ad account showed four page groups:

```text
Page/group        | Page ID          | Campaigns | Dominant status
------------------|------------------|-----------|----------------
Elena Santana     | 990898360783030  | 5         | ACTIVE
Patricia Flores   | 1063171606876651 | 5         | PAUSED
Carla Rojas       | 1037297262803284 | 5         | PAUSED
Gabriela López    | 1097045910150412 | 5         | PAUSED
```

When a clone fails on one page, first map all campaigns/adsets and promoted `page_id`s in the account before assuming the blocker applies globally.

## Retest sequence and interpretation

1. Patricia clone with valid token:
   - Campaign creation succeeded.
   - Adset creation failed with `code=100/subcode=1487202`.
   - Meta user title: page permission insufficient to publish ads.
   - Interpretation: token/user lacks enough access to the Patricia promoted page.

2. Elena clone using campaign `120248940367540604`:
   - Campaign creation succeeded.
   - Adset creation succeeded.
   - Creative creation initially hit Instagram asset access or generic creative errors depending on creative mode.
   - After omitting `instagram_user_id`, adcreative creation succeeded.
   - Final `POST /ads` failed with `code=31/subcode=3858385` pending account authentication.
   - Interpretation: alternate page bypassed the page-permission blocker, but account/user/app still has a final ad-creation security checkpoint.

## Script improvement

`/root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py` gained:

```bash
--omit-instagram-user-id
```

Use it when Meta returns:

```text
code=200/subcode=1815199
error_user_title=La cuenta publicitaria no tiene acceso a la cuenta de Instagram
```

This flag sets `instagram_user_id=None` while rebuilding `object_story_spec`, allowing a page-only creative probe. It is a diagnostic/control-path option; do not assume it is acceptable for every production creative without checking placement requirements.

## Best next retest path

If Rodolfo authenticates the account in Ads Manager and asks to retry, start with the Elena route because it already passed:

```text
Layer               | Last Elena result with --omit-instagram-user-id
--------------------|-----------------------------------------------
GET source          | OK
Create campaign     | OK
Create adset        | OK
Create adcreative   | OK
POST /ads           | blocked only by code=31/subcode=3858385
Cleanup             | campaign marked DELETED and verified
```

Recommended command shape:

```bash
ARES_META_MIN_INTERVAL_SECONDS=0 python3 /root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py \
  --account-id 1356770869843984 \
  --operation-id OpenzedFinanzas-CC-ES \
  --loser-campaign-id 120248940367540604 \
  --daily-budget-usd 25 \
  --creative-mode video_data_minimal \
  --omit-instagram-user-id
```

Keep the existing safety behavior: create PAUSED, require 3 ads for success, delete/verify partial campaign on any failure, and save audit under `data/ares/meta-ads/audit/clone/`.

## Durable pitfall

`code=31/subcode=3858385` after campaign/adset/creative succeeded is not a page-permission problem. It means the Ads Manager/account/user still has a pending authentication action blocking ad creation/modification. Do not keep generating payload variants after this point; ask Rodolfo to authenticate the account in Ads Manager, then retry the minimal Elena path.
