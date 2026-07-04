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