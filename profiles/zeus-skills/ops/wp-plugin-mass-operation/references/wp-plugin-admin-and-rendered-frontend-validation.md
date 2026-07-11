# WordPress plugin admin + rendered frontend validation

Use this when processing REPORT-INFRA or doing QA for a custom WordPress plugin that exposes public routes and an authenticated admin page.

## Durable lesson

Do not accept plugin source lint, ZIP hash, unauthenticated HTTP 200, or static/browser fixtures as proof that a WordPress plugin is working in production. Validate the deployed WordPress-rendered output and the authenticated admin surface separately.

## Public route validation

For public routes such as `/chat/emp/br1`:

1. Fetch the live URL with the exact deployed domain.
2. Confirm HTTP status and expected plugin markers exist.
3. Use a browser/DOM check against the live page, not a local fixture only:
   - `.mgs-chat-funnel-config` exists.
   - `JSON.parse(script.textContent)` succeeds.
   - `.mgs-cf-gate` or equivalent first UI state renders.
   - `document.body.innerText` is not empty when the route should show UI.
   - offer links preserve test UTMs.
4. If the page returns 200 but body is visually empty, treat it as failed even if grep finds config markers.

Common failure: PHP source uses what looks like safe JSON output, but the deployed WordPress/plugin editor/runtime still renders `&quot;...` inside `<script type="application/json">`; then `JSON.parse(script.textContent)` fails and the frontend is blank.

## Authenticated admin validation

For admin pages such as `/wp-admin/admin.php?page=mgs-chat-funnels`:

- An unauthenticated `curl` may return login redirect, 404, or a themed page depending on site hardening. That does not validate or invalidate the admin feature by itself.
- Validate admin claims with an authenticated browser/session or WP REST/admin credential flow.
- Required checks for an admin UI report:
  - menu/page title visible, e.g. `MGS Chats`;
  - expected actions visible (`Criar`, `Duplicar`, `Relatórios`, `Excluir`);
  - form fields/nonce present;
  - save/duplicate/delete actions return HTTP 200 and produce the expected persisted file/config change;
  - any temporary test route created during duplicate is deleted and no residue remains.

## REPORT-INFRA acceptance rule

For plugin/config reports, ACK only when both are true:

- repo artifact/ZIP/source validations pass; and
- the deployed runtime proof passes on the live site.

If source shows the intended fix but live deployed HTML still fails, respond with a canonical error and do not update inventory as successful deployment.

## Ad Inserter header/footer code saves behind Wordfence

Ad Inserter 2.x does not submit changed code textareas as raw HTML. Its admin JavaScript `encode_code()` converts the changed field to `:AI:` plus standard base64 before the regular form POST. Sending raw `<script>`/HTML in `code_block_h` can be blocked by Wordfence with HTTP 403 even when authentication and the WordPress nonce are valid.

Safe procedure for a narrow header-code correction:

1. Authenticate through the real hidden WordPress login and fetch `options-general.php?page=ad-inserter.php`.
2. Back up the exact current `code_block_h` value with timestamp and SHA-256 before changing it.
3. Serialize successful controls from `#ai-form`, preserving duplicate hidden+checked checkbox values and selected options.
4. Omit unchanged `code_block_*` fields from the POST. Add only the changed field as `code_block_h=:AI:<base64(UTF-8 new code)>` plus one `ai_save` submit value. Send browser-like `Origin` and `Referer` headers.
5. If an initial raw-code POST returns 403, verify by authenticated readback that no change occurred before retrying with the plugin-native encoding.
6. Require an exact authenticated readback of `code_block_h` after HTTP 200.
7. Validate the canonical public URL without a cache-busting query. Check rendered HTML plus a real browser after the intended timeout.

For preloaders affected by LiteSpeed delayed JavaScript, prefer a CSS animation failsafe that reaches `visibility:hidden`, `opacity:0`, and `pointer-events:none` after a short fixed timeout. Remove body scroll locking unless it is strictly necessary. Validate `document.body` remains scrollable and that the fix does not depend on `DOMContentLoaded`, `DOMContentLiteSpeedLoaded`, click, touch, or scroll.