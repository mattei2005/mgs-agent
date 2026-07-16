# SMS Funnel Balance Monitor

## Trigger

Use this reference when Rodolfo asks to monitor SMS Funnel credits, alert before depletion, confirm a recharge, or diagnose missing balance alerts.

## Live contract validated 2026-07-16

- Credential source: 1Password item `SMS Funnel Dashboard` in vault `MGS Conteúdo`.
- Login: `POST https://web2.smsfunnel.com.br/api/login` with the dashboard email/password.
- Authentication result: bearer `access_token`; never print, log, persist, or add it to inventory/state.
- Balance: `GET https://web2.smsfunnel.com.br/api/user-credits-info` with `Authorization: Bearer <token>`.
- Relevant fields: `total_contracted`, `total_sent`, `total_reserved`, `credits`, `total_calculated_broadcasts`.
- Reconcile every read: `total_contracted - total_sent - total_reserved - credits`; surface a non-zero gap instead of silently trusting inconsistent arithmetic.

## MGS implementation

- Script: `/root/mgs-agent/scripts/monitor-sms-funnel-balance.py`
- State: `/root/mgs-agent/data/sms-funnel-balance-state.json` (mode `0600`, ignored by Git)
- Log: `/root/mgs-agent/logs/monitor-sms-funnel-balance.log`
- Cron: hourly at minute 24 with `flock -n`.
- Discord destination: `#sms-funnel-balance` (`1527433742233374893`).
- Transport: Zeus bot API directly. Do not add a recurring 1Password webhook lookup.

Default bands:

- No alert: `credits > 10,000`
- Critical: `5,000 < credits <= 10,000`
- Emergency: `credits <= 5,000`

Behavior:

1. Stay silent while `credits > 10,000`.
2. Alert when the balance reaches `10,000` or less; mention Rodolfo.
3. At `5,000` or less, add an `Ação necessária` field instructing a PIX recharge with the SMS Funnel supplier.
4. Remind at most every 12h in critical and every 4h in emergency.
5. Detect a recharge when contracted credits increase or available balance rises by at least 100, then post a green confirmation.
6. Fetch `GET /api/daily-sents` and calculate the projection from the three most recent completed calendar days. Exclude the current partial-day bucket so the hourly execution time does not distort the average. If that endpoint fails, keep the balance alert working and mark the projection unavailable.
7. Alert after two consecutive API/1Password failures and post recovery only if that failure was previously alerted.
8. If Discord delivery fails, do not consume the state transition; retry it on the next run.
9. Keep threshold alerts minimal: show only `Saldo disponível` and `Projeção`. The projection line contains the average of the three most recent completed days in SMS/day and the estimated duration of the current balance. Do not show contracted/used credits or threshold definitions. Add `Ação necessária` only in the emergency band (`credits <= 5,000`).

## Validation

Before production or after edits:

1. `python3 -m py_compile`.
2. Live `--dry-run` proving login + credits read without state mutation.
3. Local fixture/mock HTTP tests proving activation, all thresholds, anti-spam, recharge, probe failure/recovery, Discord failure retry, allowed mentions, and state mode `0600`.
4. One real `--send-test` to the configured channel; validate returned `message_id` and channel readback.
5. Install cron through a backed-up intermediate crontab file, run `infra-discovery.sh`, regenerate `docs/CRONS.md`, append audit, and send REPORT-INFRA.

## Pitfalls

- SMS Funnel has no native low-credit notification in the observed account; the MGS monitor is the alerting layer.
- Recharge is operationally manual via the vendor/PIX; the monitor only detects and alerts—it never initiates payment.
- Do not cache the dashboard password or bearer token in `data/`; credentials remain in 1Password.
- Avoid frequent polling: hourly is sufficient for the observed burn rate and limits recurring 1Password reads.
- A dashboard session or login success is not enough; require the credit endpoint and accounting reconciliation.
