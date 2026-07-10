## Purpose

This is the canonical access route for Smart Bidding (`https://app.smartbiddingdigital.com/`) used by MGS agents.

Load this skill whenever Rodolfo asks an agent to:

- log into SB / Smart Bidding;
- inspect `/accounts`;
- navigate Messenger `Page` or `Broadcast Template`;
- inspect `Reports > Messenger Daily` or `Reports > Messenger Pages`;
- export reports or read delivered/leads/revenue tables;
- debug Auth0 login or `BotGuardError`;
- repeat a previous Zeus route that successfully entered the SB dashboard.

## Critical Lesson

Do **not** default to Playwright headless for SB dashboard navigation.

Headless can authenticate with Auth0 and still fail inside the SB runtime with:

```text
BotGuardError: Automated browser detected
Failed to validate user; attempting cookie fallback
```

This is not a bad-password signal. It means the browser automation mode was detected.

The route that worked for Zeus was **Playwright headed under Xvfb**:

```text
Playwright Chromium
headless=False
xvfb-run -a
--disable-blink-features=AutomationControlled
normal Chrome user-agent
persistent storage_state: /tmp/smartbidding_state_headed.json
```

## Canonical Command Pattern

Use the existing venv when present:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
xvfb-run -a /tmp/sb-venv/bin/python <script>.py
```

If `/tmp/sb-venv` is missing, create a temporary venv and install Playwright before use:

```bash
python3 -m venv /tmp/sb-venv
/tmp/sb-venv/bin/pip install --quiet playwright
/tmp/sb-venv/bin/python -m playwright install chromium
```

Avoid installing Playwright system-wide. Ubuntu may block system pip via PEP 668.

## Browser Context Pattern

In Python/Playwright:

```python
browser = await p.chromium.launch(
    headless=False,
    args=["--disable-blink-features=AutomationControlled"],
)
ctx = await browser.new_context(
    storage_state="/tmp/smartbidding_state_headed.json",
    viewport={"width": 1600, "height": 1000},
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
)
```

If there is no valid storage state yet, create the context without `storage_state`, perform login, then save it:

```python
await ctx.storage_state(path="/tmp/smartbidding_state_headed.json")
```

## Credentials

The 1Password item used by Zeus is:

```text
Item: Zeus - Smartbidding Dashboard
Vault: MGS Conteúdo
URL: https://app.smartbiddingdigital.com
```

Never print the password/token/session in chat or logs.

When retrieving a concealed password through `op`, use `--reveal`:

```bash
op item get 'Zeus - Smartbidding Dashboard' \
  --vault 'MGS Conteúdo' \
  --field password \
  --reveal
```

Without `--reveal`, `op` can return a masked/reference-like value. Auth0 may then show `Wrong email or password` even though the human credential is valid.

## Fresh Login Flow

1. Start headed Playwright under Xvfb.
2. Go to the target URL, usually:

```text
https://app.smartbiddingdigital.com/accounts
```

3. If redirected to Auth0, fill:
   - email/username from 1Password;
   - password from 1Password with `--reveal`.
4. Click `Continue`.
5. Wait for SB app to load.
6. Confirm body text contains the dashboard and user `Zeus - Agent`.
7. Save storage state:

```python
await ctx.storage_state(path="/tmp/smartbidding_state_headed.json")
```

## Known Good Verification

A successful access check should look like:

```text
url   https://app.smartbiddingdigital.com/accounts
title Accounts
user  Zeus - Agent
botguard False
```

The `/accounts` page loaded with visible sidebar/menu:

```text
Dashboard
Reports
Inventory
Smart Routing
Ads Pilot
IA Content
Quiz Maker
OKRS
```


## Mandatory fresh-session/full-scope rule

Before any Smart Bidding action/write, start from a fresh authenticated session: logout/login when practical, then select/filter the full MGS Messenger scope: all sites/publishers under `digital-trust` and `digital-trust-2`. Do not act from a stale UI/API context, partial 45-site capture, default company, or cached state. Validate the full Page scope before writes (expected current full table baseline: `/campaigns/Messenger` live rows around 3,237; the UI label may vary, but both companies must be included).

## Messenger Navigation Route

From `/accounts`:

1. Use the top source/context dropdown.
2. Select `Messenger`.
3. Confirm tabs appear:

```text
Account
User
Page
Broadcast Template
```

