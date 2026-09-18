# PubGuru/M2 revenue reconciliation

## Authority and scope

- Rodolfo `1550520908517478583`, period correction `1550520995335503945`, campaign-prefix rule `1550521965805043746`, thread `1545426987756298340`.
- Applies to MonetizeMore/PubGuru M2 revenue for `wantabrand.com` and `finance.wantabrand.com`.
- Access is read-only through the Hermes local vault handle labeled `PubGuru M2`, bound to origin `https://app.pubguru.com`. Never expose credentials, session cookies, or API tokens.

## Permanent classification rule

1. Normalize `utm_campaign` with trim + lowercase.
2. Any value beginning with the literal prefix `b01` is **tráfego direto**.
3. Every other value, including `/empty/`, is **BOT/ChatPion**.
4. Preserve each literal campaign value in evidence; never rewrite the source label.

## Canonical audit procedure

1. In Profit Attribution, select `utm_campaign`, USD and the exact domain.
2. The report enforces a maximum three-day range. Split a month into contiguous nonoverlapping windows of at most three days.
3. Collect both domains for every window, persist sanitized rows, deduplicate programmatically by `domain + start_date + end_date`, and assert the expected range count before totaling.
4. Sum gross revenue by literal campaign, then partition Direct versus BOT using the prefix rule above.
5. In Analytics Report, use the full same month, exact domain, USD and `Revenue Source = NETWORK`; sum daily gross.
6. Reconcile for each domain and combined:
   - Direct + BOT from Profit Attribution;
   - NETWORK gross from Analytics;
   - M2 gross in the finance dashboard.
7. Report a difference rather than changing the dashboard. A divergence between two PubGuru reports is an upstream-source inconsistency until PubGuru/MonetizeMore or Rodolfo identifies which source governs.

## August 2026 validated read-only observation

- Dashboard production, cutoff 31/08:
  - `wantabrand.com`: USD `5150.28`.
  - `finance.wantabrand.com`: USD `7.40`.
  - Combined: USD `5157.68`.
- Profit Attribution, 11 nonoverlapping windows per domain, 22 unique domain/range records:
  - Direct: USD `519.89`; only `b01fb01c01` appeared under the `b01` prefix.
  - BOT: USD `4628.86`, including `/empty/` as authorized.
  - Combined: USD `5148.75`.
  - `wantabrand.com`: Direct `519.89` + BOT `4621.03` = `5140.92`.
  - `finance.wantabrand.com`: Direct `0.00` + BOT `7.83` = `7.83`; campaign `pg-19326`.
- Analytics Report NETWORK gross:
  - `wantabrand.com`: USD `4604.04`.
  - `finance.wantabrand.com`: USD `7.83`.
  - Combined: USD `4611.87`.
- Reconciliation:
  - Profit Attribution exceeds Analytics by USD `536.88`, entirely in `wantabrand.com`.
  - Dashboard exceeds Profit Attribution by USD `8.93` combined.
  - Dashboard exceeds Analytics by USD `545.81` combined.
  - The main-domain gap is concentrated in 01–06 and 13–21 August; the other bounded windows reconcile to rounding.
- Conclusion: Direct/BOT classification is computable, but Profit Attribution does not equal Analytics for the main domain. No dashboard mutation is authorized from this observation.

## Evidence

- Report: `/root/mgs-agent/reports/finance-pubguru-m2-august-20260918.md`.
- Sanitized browser evidence: profile-local browser workspace `pubguru_profit_august_2026_dedup.json` and `pubguru_analytics_august_2026.json`; never persist URLs containing session/API tokens.
