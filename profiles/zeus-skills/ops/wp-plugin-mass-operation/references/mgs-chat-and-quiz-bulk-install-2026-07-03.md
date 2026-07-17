# MGS chatzinho + quiz — bulk install pattern (2026-07-03)

Use this reference when Rodolfo asks to install the `MGS Chat Funnels` plugin plus the quiz plugin across a mixed RunCloud + Bitnami/WP Admin site list.

## Plugins validated in this session

- Chatzinho: `mgs-chat-funnels` version `0.3.9`, package source `/root/mgs-agent/plugins/mgs-chat-funnels`.
- Quiz: `activecampaign-quiz-lazy-blocks` version `1.1`.
  - In this session the quiz package was not present in `/root/mgs-agent/plugins`; it was extracted from an existing installed copy on `finance.topfeed.fun` and repackaged as a zip.
  - Treat this as a valid fallback when the plugin is already deployed on one target and Rodolfo asks for replication, but still lint PHP and validate the zip before installing elsewhere.

## Durable workflow

1. Validate the chat package before deploy:
   - `php -l` every PHP file.
   - `node --check assets/chat-funnels.js`.
   - `python3 -m json.tool configs/*.json`.
   - `zip -qr /tmp/mgs-chat-funnels.zip mgs-chat-funnels` and `unzip -tq`.
2. Locate/prepare the quiz package:
   - First search local plugin sources.
   - If missing, audit target sites for an existing installed plugin via `wp plugin list | grep -Ei 'quiz|funnel|chat'`.
   - If a known-good site has it, `tar` the plugin directory from `wp-content/plugins`, extract locally, run `php -l`, then zip the plugin directory.
3. RunCloud sites:
   - Copy both zips to the server.
   - Use `sudo -n` for path checks and file operations under `/home/runcloud*`; the `zeus` SSH user may not have direct read/list permissions even though passwordless sudo works.
   - Use the owning webapp user for WP-CLI: `runcloud` vs `runcloud2`.
   - Backup existing plugin directories by copying to `plugin-slug.zeus-bak-YYYYMMDD-HHMMSS` before overwrite.
   - Install with `wp plugin install ZIP --force --activate`.
4. Bitnami/WP Admin sites such as `openzed.com` and `cliquet.com`:
   - Login at the custom `/rodloguda/` URL from 1Password.
   - Use `plugin-install.php?tab=upload`.
   - If WordPress shows “already exists / Replace current with uploaded”, follow the replace link, then verify activation from the plugin list.
   - REST plugin management may be blocked or incomplete; WP Admin upload/replace remains acceptable when validated after.
5. Validation before reporting success:
   - For every site, verify `mgs-chat-funnels` active + expected version.
   - Verify `activecampaign-quiz-lazy-blocks` active + expected version.
   - Fetch `/chat/car/br1/` and `/chat/emp/br1/` with a cachebuster and confirm HTTP status plus ad-wrapper markers where applicable.
   - If a site has the plugin active but routes return WP 404, report that as a separate routing conflict instead of claiming full route readiness.

## Pitfalls observed

- Direct `test -d` / `ls /home/...` over SSH can falsely look like “path missing” because `/home` is permission-restricted. Retry with `sudo -n test -d` before changing the inventory assumption.
- `wp plugin install --force` may print “Removing the old version” even for a new install; trust the final `wp plugin get` validation, not the install prose alone.
- `wantabrand.com` may emit the known `yoast-rest-meta.php` mu-plugin permission warning during WP-CLI. It did not block plugin installation/activation; still surface it if seen.
- `cliquet.com` can show both plugins active while `/chat/...` routes return the theme/WP 404 page. Do not remediate routing automatically unless Rodolfo asks; separate install success from route readiness.
- When `class-mgs-chat-sms.php` is embedded inline into the main plugin file for Bitnami/WP Admin, `__DIR__` changes from `plugin/includes` to the plugin root. Rewrite only the config lookup from `dirname( __DIR__ ) . '/configs/'` to `__DIR__ . '/configs/'` in the generated inline artifact. Otherwise `/chat-sms/` renders but transactional submissions fail with `Chat SMS não encontrado.` Validate the generated artifact by shell hash, PHP lint, exact config-path readback, and a mocked insert/delete smoke with the original row count restored before promotion.
