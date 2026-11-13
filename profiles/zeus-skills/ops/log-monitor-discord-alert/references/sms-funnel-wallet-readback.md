# SMS Funnel: wallet API and dashboard reconciliation

Use for a live balance check or credits-vs-wallet alert diagnosis. Pair with local-browser-automation/references/credentialed-dashboard-readonly-audit.md for secure unattended form login.

## Authoritative reads

- Public current dashboard: https://app2.smsfunnel.com.br/#/login. The old web2 HTML root redirects to app2; HTML transport may return 403 while the API works.
- Canonical internal credential/login helper: `/root/mgs-agent/scripts/monitor-sms-funnel-balance.py` exports `runtime_env`, `read_credential`, and `http_json`. Credentials remain inside the process, with explicit 1Password vault; never emit them or the login response.
- API base is https://web2.smsfunnel.com.br/api, confirmed in the current dashboard public environment JS.
- Authenticated GET `/wallet/balance`: require BRL, numeric `available_micros`, `balance_micros`, `held_micros`. Use Decimal / 1000000 for BRL. Missing/invalid fields are unknown, never zero.
- Authenticated GET `/wallet/billing`: e.g. channel value `wallet` means that channel uses the financial wallet instead of its legacy credits bucket. Do not interpret `/user-credits-info.credits == 0` as zero financial balance for a wallet-billed channel.

## Independent browser acceptance

1. Use an isolated local Chromium context and a genuine login form, reading credentials internally from the canonical helper. Select `input[type=email]`, `input[type=password]`, then the ENTRAR button. Stop on MFA/challenge; do not alter account security or use a session import to claim a form login.
2. If Playwright is absent from the current interpreter, prefer a temporary `uv run --with playwright --python 3.12 python` invocation and reuse an already installed compatible Chromium executable. Discover its path; do not install browsers or modify protected agent browser caches just for the check.
3. Wait for `SALDO GERAL DA CONTA` after navigation to `#/dashboard`, not merely the authenticated greeting or route. Read the rendered amount and `reservados em envios`; loading placeholders do not pass.
4. Optionally query `/wallet/balance` from the authenticated page using its in-memory/localStorage session without printing session data. Compare the same exact wallet amount, currency, and reserves against the direct API response and screenshot.
5. Close the temporary context/browser and clear any temporary credential/session artifacts. Never output passwords/tokens, unrelated account data, or screenshots unless requested.

A transferred API session that briefly renders the greeting then returns to login is not a completed dashboard check. Diagnose its status without claiming an IP/anti-bot cause. A successful fresh form login plus the loaded wallet card is the browser acceptance gate.

## Reporting

Say separately: API balance confirmed, authenticated dashboard balance confirmed, comparison result, and monitor deployment state. Saving this procedure does not patch the credits-based monitor. Do not claim monitoring recovered until the consumer itself is corrected and tested.
