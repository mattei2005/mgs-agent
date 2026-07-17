# Webshare/AdsPower proxy test for Meta `POST /ads` — 2026-06-18

## Context

Rodolfo suspected the MGS VPS provider/IP (Hetzner, Ashburn) was causing challenges in Meta and YouTube/agente legado workflows. agente legado/YouTube showed a clear browser anti-bot symptom (`Sign in to confirm you’re not a bot`) from VPS browser. For Ares/Meta, the failure was more specific: campaign/adset/adcreative creation could work, but `POST /ads` returned Meta checkpoint/pending-action errors.

System User was explicitly out of scope per Rodolfo.

## Proxy source

Rodolfo uses Webshare inside the Marcos AdsPower profile. He saved a 1Password item named:

```text
Proxy AdsPower Marcos Meta
```

Fields used:

```text
Username    proxy username
Credential  proxy password
Host        proxy host/address
Port        proxy port
Protocol    http
```

Do not print these values. Use internally only.

## Validation performed

Direct VPS egress:

```text
IP       [EGRESS HETZNER APOSENTADO — NÃO USAR]
Org      Hetzner Online GmbH
Region   Ashburn, Virginia, US
```

Proxied egress through Webshare/AdsPower item:

```text
IP       9.142.28.173
ISP      Comcast Cable Communications, LLC
Region   Sacramento, California, US
Proxy    ip-api flagged proxy=true
```

This proved the script could route through the Webshare proxy and Meta calls were no longer leaving directly from Hetzner.

## Scripts tested

Legacy script first, then corrected video-id script:

```text
/root/mgs-agent/scripts/ares-meta-replacement-clone.py
/root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py
```

Python `urllib.request` honored `HTTPS_PROXY` / `HTTP_PROXY`; no code patch was needed to force proxy for the test.

Dry-run command shape:

```bash
HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" \
python3 /root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25 \
  --creative-count 3 \
  --creative-mode video_data_minimal \
  --dry-run
```

Controlled write command shape, after explicit approval:

```bash
HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" \
python3 /root/mgs-agent/scripts/ares-meta-replacement-clone-videoid.py \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25 \
  --creative-count 3 \
  --creative-mode video_data_minimal
```

## Results

Dry-run through proxy:

```text
status       dry_run_ok
campaign     Patricia Flores - US - ESP - (pg_22069) - RPL - 20260619 - 01
winners      3 selected by CPMO
```

Controlled write through proxy with corrected video-id flow:

```text
Step                         Result
---------------------------- ------------------------------------
create_campaign              OK
create_adset                 OK
create_adcreative            OK via video_id / video_data_minimal
create_ad                    failed
Meta error                   code=31 / subcode=3858385
User title                   Autentica tu cuenta
Partial campaign             120248897718590604
Cleanup                      DELETED and verified
```

Legacy accidental write also created a partial campaign and was cleaned manually:

```text
120248897549500604 -> DELETED, verified by GET
```

## Interpretation

The Webshare/AdsPower proxy did **not** resolve Meta `POST /ads`.

Durable conclusion for future sessions:

```text
If direct Hetzner and residential/Webshare proxy both fail on POST /ads, while campaign/adset/adcreative succeed, do not frame the issue as “just Hetzner/IP.” It is more likely an app/token/API trust or endpoint-specific Meta validation block for ad creation/modification.
```

Endpoint boundary matters:

```text
Campaign API       OK
Adset API          OK
Adcreative API     OK
POST /ads          blocked
```

The next practical path, with System User excluded, is not another raw proxy retry. Options are:

1. Browser/Ads Manager automation in the known-good AdsPower profile/session.
2. Investigate exact UI request flow used by Ads Manager when Marcos duplicates manually.
3. Try another app/token only if Rodolfo provides it, but do not propose System User again unless he reopens that path.

## Reporting pitfall

Report both the proxy evidence and the endpoint-specific failure. Do not overclaim that Hetzner is innocent globally: Hetzner/datacenter remains a strong cause for agente legado/YouTube browser challenges. The Meta finding is narrower: proxy did not fix `POST /ads`.
