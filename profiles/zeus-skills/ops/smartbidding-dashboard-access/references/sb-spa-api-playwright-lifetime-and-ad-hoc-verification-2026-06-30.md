# Playwright SPA API update lifetime + verification notes — 2026-06-30

Session lesson from bulk-updating SB Messenger Broadcast Templates via the authenticated SPA API.

## API context lifetime pitfall

If a helper captures `/broadcast/Messenger` rows/headers inside:

```python
async with async_playwright() as p:
    browser = await p.chromium.launch(...)
    ctx = await browser.new_context(...)
    return ctx, page, rows, headers, post_url
```

then the returned `ctx/page` are already invalid because leaving `async with async_playwright()` stops Playwright and closes browser/context. Later `ctx.request.post(...)` fails with errors like:

```text
TargetClosedError: APIRequestContext.post: Target page, context or browser has been closed
```

## Correct pattern

Keep Playwright/browser/context alive through the POST sequence:

```python
p = await async_playwright().start()
browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
ctx = await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json', ...)
page = await ctx.new_page()
# capture rows + request headers
# run ctx.request.post(...) updates here or return p,browser,ctx,page and close later
try:
    ...
finally:
    await browser.close()
    await p.stop()
```

If closure can race with a page already closed, wrap cleanup in best-effort `try/except` but do not ignore failures during POST/update.

## Verification expectation for generated operational scripts

For one-off scripts that perform SB/Sheet transformations, run an ad-hoc verification script under `/tmp` after edits when no canonical test suite exists. Use a filename prefix like:

```text
/tmp/hermes-verify-*.py
```

The verification should avoid touching production systems and cover pure behavior such as:

- `ast.parse` and module import;
- `status_of()` precedence;
- zero-width stripping;
- target link rotation/preservation;
- CSV tempfile readback.

Report it as **ad-hoc verification**, not suite green.
