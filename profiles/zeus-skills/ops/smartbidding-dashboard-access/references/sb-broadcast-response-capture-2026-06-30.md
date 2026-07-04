# SB `/broadcast/Messenger` extraction via captured app response — 2026-06-30

## Context

During a GB-CC-EN Utility Template preparation, direct calls from Playwright's `ctx.request.get()` to:

```text
https://api.jbfdigital.com.br/broadcast/Messenger?companies[]=digital-trust&companies[]=digital-trust-2&source=Messenger
```

returned `401 Unauthorized`, even though the headed SB session was logged in and the UI worked.

The reliable path was to trigger the real SB frontend flow and capture the network response emitted by the app.

## Pattern

Use headed Playwright/Xvfb with the persistent SB storage state. Attach a response listener before selecting Messenger / Broadcast Template:

```python
captured = []

async def on_resp(resp):
    if '/broadcast/Messenger' in resp.url:
        try:
            txt = await resp.text()
            captured.append({'url': resp.url, 'status': resp.status, 'text': txt})
        except Exception as e:
            captured.append({'url': resp.url, 'status': resp.status, 'error': str(e)})

page.on('response', on_resp)
await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle')
await page.locator('.p-dropdown').first.click()
await page.get_by_text('Messenger', exact=True).last.click()
await page.get_by_text('Broadcast Template', exact=True).click()
await page.wait_for_timeout(6000)

good = [c for c in captured if c.get('status') == 200 and c.get('text','').strip().startswith('[')]
rows = json.loads(good[-1]['text'])
```

Then filter rows locally, for example:

```python
targets = [r for r in rows if 'Newsoun - GB-CC-EN' in (r.get('NAME') or '')]
msgs = targets[0].get('MESSAGES')
if isinstance(msgs, str):
    msgs = json.loads(msgs) if msgs.strip().startswith('[') else []
links = [m.get('LINK_1') or m.get('LINK 1') or '' for m in msgs]
```

## Why this matters

- The app may attach auth or runtime headers that are not available to `ctx.request` directly.
- Do not downgrade this to "API is unavailable" if UI works. Capture the UI's own API response instead.
- This is especially useful for extracting exact template `MESSAGES` JSON and preserving link sequences for import CSVs.

## Safety

- Never print bearer tokens, cookies, Auth0 state, or passwords.
- The captured response body is operational data; summarize counts and safe fields in chat.
- Keep raw snapshots under work/backups paths, not in Discord unless Rodolfo asks for the file.
