# MGS Chat Funnels — Ad wrapper admin fields and verification

Session pattern from OpenZed chat funnel maintenance.

## Durable lesson

For `MGS Chat Funnels`, rewarded/interstitial ads are controlled by two separate concerns:

1. **Frontend behavior**: `rewarded_enabled`, auction count, timeout/fallback, and chat unlock behavior.
2. **Ad wrapper identity**: the JBF builder URL that must match the company/site pair.

Do not leave the wrapper URL as a hard-coded legacy domain such as FincFrog when migrating the chat to another site.

## Preferred admin UI

Add explicit fields in the human editor under monetization/tracking:

- `Company do wrapper`
  - default: `digital-trust`
  - example: `digital-trust`
- `Domain do wrapper`
  - example: `openzed`
  - if blank, derive from `home_url()` host, stripping `www.` and taking the root domain label where appropriate.
- `Wrapper gerado`
  - show a read-only preview so the operator can see exactly what will load.

Wrapper format:

```text
https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js
```

Example for OpenZed:

```text
https://assets.jbfdigital.com.br/assets/digital-trust/openzed/digital-trust_openzed.builder.js
```

## Label copy improvement

Avoid vague labels like:

```text
Rewarded/interstitial ativo
Se falhar, o plugin libera o chat via fallback.
```

Use operator-facing copy:

```text
Exigir anúncio antes de liberar o chat
Quando ativo, o chat tenta exibir rewarded/interstitial antes de continuar. Se o anúncio falhar ou expirar, o chat será liberado automaticamente pelo fallback.
```

## Implementation notes

- Enqueue `https://securepubads.g.doubleclick.net/tag/js/gpt.js` when rewarded ads are enabled.
- Enqueue the generated wrapper URL before the chat frontend script.
- For full-page route rendering, call the asset enqueue logic before `wp_head()`. If enqueue only happens inside the rendered body/container after `wp_head()`, WordPress will not print those scripts in the document head/footer for route-rendered pages.
- Keep fallback behavior: if `window.jbftag.showRewardedAds` is unavailable or times out, unlock the chat rather than trapping the user.

## Safe deploy path on Bitnami/OpenZed when only WP admin is available

If REST plugins endpoint only supports activate/deactivate and there is no writable SFTP/SSH, the WordPress Plugin Editor can update a plugin file with WordPress recovery checks:

1. Login via `https://SITE/rodloguda/`.
2. With curl, seed `wordpress_test_cookie` manually if WordPress rejects cookies in non-browser login.
3. Fetch:
   ```text
   /wp-admin/plugin-editor.php?file=mgs-chat-funnels%2Fmgs-chat-funnels.php&plugin=mgs-chat-funnels%2Fmgs-chat-funnels.php
   ```
4. Extract `nonce` and `<textarea name="newcontent">`.
5. Save the remote textarea content as backup before posting changes.
6. POST `action=update`, `nonce`, `file`, `plugin`, `newcontent` back to `plugin-editor.php`.
7. Verify REST plugin version/status and public routes.

This is safer than WPCode snippets for plugin file updates because WordPress performs plugin editor safety checks and the file is not executed as an ad-hoc snippet.

## Ad-hoc verification checklist

Use a temporary `/tmp/hermes-verify-*` script for focused verification when there is no canonical test suite:

- `php -l` on the changed plugin PHP file.
- `node --check` on `assets/chat-funnels.js`.
- `python3 -m json.tool` on bundled config JSON files.
- Reflection/stub test of the wrapper URL helper if WordPress runtime is not locally available.
- Remote HTML checks for each live route:
  - HTTP 200
  - contains `securepubads.g.doubleclick.net/tag/js/gpt.js`
  - contains `{company}_{domain}.builder.js`
  - contains `mgs-chat-funnel-config`
- Admin page check after login:
  - `name="ad_company"`
  - `name="ad_domain"`
  - improved label text
  - wrapper preview

Report this explicitly as ad-hoc/focused verification, not as full suite green.
