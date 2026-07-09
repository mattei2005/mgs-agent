# Custom WP plugin public routes — global WordPress hooks

Session learning: OpenZed `MGS Chat Funnels` canary, 2026-07-08.

## Rule

When a custom MGS WordPress plugin exposes public URLs such as `/chat/...` or quiz routes, those URLs should normally behave like regular WordPress URLs, not isolated static HTML islands.

If Rodolfo changes site-wide integrations — WPCode Header/Footer, GTM, Yoast, pixels, head scripts, footer scripts, tracking plugins, SEO plugins, or future global site tooling — the plugin route must inherit those changes unless he explicitly asks for a fully isolated standalone file.

## Preferred implementation pattern

For route renderers that output their own full HTML template, keep the visual template clean but call the core WP hooks:

```php
private function capture_wp_head() {
    ob_start();
    wp_head();
    $output = ob_get_clean();
    return is_string($output) ? $output : '';
}

private function capture_wp_body_open() {
    ob_start();
    if (function_exists('wp_body_open')) {
        wp_body_open();
    } else {
        do_action('wp_body_open');
    }
    $output = ob_get_clean();
    return is_string($output) ? $output : '';
}

private function capture_wp_footer() {
    ob_start();
    wp_footer();
    $output = ob_get_clean();
    return is_string($output) ? $output : '';
}
```

Template placeholders:

```html
<head>
  ...plugin CSS...
  {{WP_HEAD}}
  ...plugin ad/wrapper head...
</head>
<body>
  {{WP_BODY_OPEN}}
  ...plugin UI...
  {{WP_FOOTER}}
</body>
```

## Validation checklist

After canary deploy, validate with a cachebuster:

```bash
python3 - <<'PY'
import requests,re
for url in ['https://SITE/chat/car/br1?hook_check=1','https://SITE/chat/emp/br1?hook_check=1']:
    r=requests.get(url,timeout=25,headers={'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache'})
    html=r.text
    print(url, r.status_code, sorted(set(re.findall(r'GTM-[A-Z0-9]+', html))), 'yoast' in html.lower(), 'id="chat-container"' in html)
PY
```

Expected for OpenZed canary:

- HTTP 200.
- `GTM-W89PNV47` present on `/chat/car/br1` and `/chat/emp/br1`.
- Yoast/global plugin markers present.
- Chat shell still present.
- No unreplaced `{{PLACEHOLDER}}` tokens.
- Browser smoke: gate opens, CTA/rewarded path works, console has no critical JS errors.

## Rollout rule

Canary first on the site Rodolfo named. After he validates in GTM/Preview, roll out to all sites where the same custom plugin is installed.

Also audit related custom plugins such as `MGS Quiz` / `activecampaign-quiz-lazy-blocks`: public quiz URLs must be checked for the same global-hook inheritance. Do not assume quiz routes inherit global WP just because the chat route has been fixed.

## Pitfall

Do not solve this by adding a “GTM field” or hardcoding a GTM container inside the plugin. Rodolfo manages pixels/events in GTM and site-wide tooling in WordPress. The plugin’s job is to keep its public routes open to WordPress global hooks.