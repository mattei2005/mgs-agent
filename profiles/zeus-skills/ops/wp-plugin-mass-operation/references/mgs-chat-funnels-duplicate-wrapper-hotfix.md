# MGS Chat Funnels — Duplicate GPT/JBF Wrapper Hotfix

Use this reference when a chat route such as `/chat/car/br1` loads `gpt.js` or `assets.jbfdigital.com.br/...builder.js` more than once.

## Symptom

Live HTML/browser shows duplicate ad stack imports, commonly:

- `https://securepubads.g.doubleclick.net/tag/js/gpt.js` twice;
- one contextual wrapper from WordPress/head/WPCode/theme, e.g. `digital-trust_cliquet_facebook_br.builder.js`;
- one plugin-rendered wrapper, e.g. `digital-trust_cliquet.builder.js`.

Ciro/JBF confirmed this is invalid: GPT should import together with the wrapper contract, but each exactly once per route.

## Root cause pattern

`MGS Chat Funnels` standalone route renders a template with:

- captured WordPress head: `{{WP_HEAD}}` from `wp_head()`;
- plugin-owned ad stack: `{{ADS_HEAD}}`.

If WordPress head/theme/WPCode also injects JBF/GPT, the final standalone HTML has two ad-stack layers.

## Safe fix pattern

Do not remove GPT/wrapper globally from WordPress. For plugin chat routes, make the plugin route own the ad stack and sanitize only the captured `wp_head()` output before inserting it into the standalone template.

Patch shape in `mgs-chat-funnels.php`:

1. Pass config to head capture:

```php
'{{WP_HEAD}}' => $this->capture_wp_head($config),
```

2. Sanitize captured head for JBF routes:

```php
private function capture_wp_head($config = null) {
    ob_start();
    wp_head();
    $output = ob_get_clean();
    if (!is_string($output)) {
        return '';
    }
    return $this->sanitize_captured_wp_head($output, $config);
}

private function sanitize_captured_wp_head($output, $config = null) {
    if (!is_array($config) || (($config['ads_enabled'] ?? true) === false) || $this->ad_provider($config) === 'm2') {
        return $output;
    }

    $patterns = array(
        '#<script\b[^>]*src=["\'][^"\']*securepubads\.g\.doubleclick\.net/tag/js/gpt\.js[^"\']*["\'][^>]*>\s*</script>#i',
        '#<script\b[^>]*src=["\'][^"\']*assets\.jbfdigital\.com\.br/[^"\']*\.builder\.js[^"\']*["\'][^>]*>\s*</script>#i',
        '#<script\b[^>]*>[\s\S]*?window\.wrapper_url\s*=\s*["\'][^"\']*assets\.jbfdigital\.com\.br/[^"\']*\.builder\.js[^"\']*["\'][\s\S]*?</script>#i',
    );

    return preg_replace($patterns, '', $output);
}
```

The third regex intentionally uses `[\s\S]*?` instead of a non-newline dot expression because the injected `window.wrapper_url` block may span multiple lines.

## Bitnami/cliquet deployment path used successfully

For `cliquet.com` Bitnami, SFTP `wpfiles` is read-only and WP File Manager may return `403` even for an admin. The successful write path was WordPress Plugin File Editor:

1. Download current file read-only via SFTP for backup:
   - `wp-content/plugins/mgs-chat-funnels/mgs-chat-funnels.php`
2. Patch locally and run `php -l`.
3. Login to `https://SITE/rodloguda/` using browser/admin credentials from 1Password.
4. Open:
   - `/wp-admin/plugin-editor.php?file=mgs-chat-funnels%2Fmgs-chat-funnels.php&plugin=mgs-chat-funnels%2Fmgs-chat-funnels.php`
5. Extract hidden `nonce` from the editor form.
6. POST to `/wp-admin/plugin-editor.php` with:
   - `nonce`
   - `_wp_http_referer`
   - `newcontent`
   - `action=update`
   - `file=mgs-chat-funnels/mgs-chat-funnels.php`
   - `plugin=mgs-chat-funnels/mgs-chat-funnels.php`
7. Re-fetch editor textarea and compare SHA-256 against local patched content.

Use this path only when Plugin File Editor is available and the file is not too large for form POST. Avoid WPCode snippets for PHP file writes on Bitnami.

## Required validation before reporting fixed

Run both raw HTML and browser runtime checks.

Raw HTML for the exact traffic URL and a bare/cachebuster URL:

- HTTP 200;
- `gpt_count == 1`;
- `wrapper_count == 1`;
- wrapper is the intended base wrapper, e.g. `digital-trust_cliquet.builder.js`;
- contextual duplicate such as `facebook_br_count == 0`;
- `window.wrapper_url_count == 0` when it came from the stripped head layer.

Browser runtime:

- `!!window.googletag === true`;
- `!!window.jbftag === true`;
- `document.scripts` has one GPT script and one JBF wrapper;
- `googletag.pubads().getSlots()` has exactly one rewarded slot unless Ciro/JBF explicitly changed the contract;
- click through the first gate to confirm the route still advances.

## Reporting pattern

Keep final report short:

- what changed;
- exact live counts after fix;
- browser runtime result;
- backup/readback status.

Do not paste credentials, raw WordPress cookies, or full plugin contents.
