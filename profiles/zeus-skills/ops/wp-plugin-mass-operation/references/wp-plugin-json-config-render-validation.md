# WordPress plugin JSON config render validation

Use this when validating a custom WordPress plugin that embeds JSON configuration into frontend HTML, especially chat/funnel/rendering plugins.

## Lesson

Raw static browser fixtures can pass while the actual WordPress shortcode/route fails if the plugin escapes JSON incorrectly before placing it inside a `<script type="application/json">` block.

Validated pitfall: `esc_html($json)` inside `<script type="application/json" class="..."><?php echo esc_html($json); ?></script>` converts quotes to entities such as `&quot;`. A fixture that injects raw JSON directly will initialize, but the real WP-rendered DOM can produce invalid JSON for `JSON.parse(script.textContent)` and the funnel renders blank.

## Validation requirement

For plugins that render JSON config to the frontend, validate the real rendered output path, not only source files or synthetic fixtures:

1. Lint source files:
   - `node --check assets/*.js`
   - `python3 -m json.tool configs/*.json`
   - `php -l plugin.php` locally or remotely.
2. Inspect the PHP render function for JSON escaping.
   - Prefer WordPress-safe JSON script output such as `wp_json_encode(...)` followed by an escaping method that does not entity-encode quotes in a way that breaks `JSON.parse` from `textContent`.
   - If using HTML escaping, run a browser test against the exact rendered HTML, not a raw JSON fixture.
3. Browser-test both modes through the same DOM shape the plugin emits:
   - container `.mgs-chat-funnel`
   - child `<script type="application/json" class="mgs-chat-funnel-config">...actual emitted content...</script>`
   - child `.mgs-chat-funnel-root`
4. Confirm initialization by checking visible gate/header text and at least one offer/call link with UTM passthrough.
5. If the fixture manually injects raw JSON, label it as a renderer-only test; it does not validate the WordPress PHP output path.

## Report-infra consequence

Do not ACK a plugin/config REPORT-INFRA as registered if validation exposes a frontend render bug. Reply with the canonical error ACK and include the blocker in one line.
