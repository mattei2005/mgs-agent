---
name: hosting-control-panel-mail
description: "Operate and troubleshoot self-hosted mail/webmail stacks on VPS control panels (HestiaCP/VestaCP): Roundcube/SnappyMail publication, DNS/mail host routing, Nginx/PHP-FPM configs, IMAP/SMTP validation, database setup, and safe credential handling."
tags: [hestia, vesta, roundcube, webmail, mail, nginx, php-fpm, mysql, dns, vps, control-panel]
related_skills: [discord-ops, log-monitor-discord-alert]
---

# Hosting Control Panel Mail — Hestia/Vesta Webmail Ops

## When to use
Use this skill when Rodolfo asks to fix, enable, audit, or explain access to e-mail/webmail on a VPS control panel, especially:

- HestiaCP/VestaCP mail domains and accounts
- Roundcube or SnappyMail not opening
- `mail.domain.com`, `webmail.domain.com`, `/webmail`, or `/roundcube` returns 404/500
- IMAP/SMTP works in Outlook/eM Client/Thunderbird, but browser webmail does not
- Cloudflare DNS points `mail`/`webmail` to the VPS and proxy status/SSL needs review
- The server has root SSH in 1Password and the task is to repair the webmail URL

## Security rules
- Never print passwords, DB DSNs, tokens, Hestia session tokens, application passwords, or full URL tokens.
- 1Password lookups are internal. Report only the item name and `len=N` for secrets when needed.
- For production VPS changes, follow AGENT.md levels:
  - read-only audit is free;
  - user-requested service/config/package changes can proceed after explicit approval;
  - critical subset needs double-confirm, especially `/etc`, `/usr`, package installs, DB user/password creation, firewall/SSH, or deletion.
- Before touching configs, create timestamped backups under `/root/zeus-<topic>-<timestamp>/` or equivalent.
- Do not use `curl -k` as proof of public TLS health. For final validation, use certificate-verifying `curl` against the public URL.

## Read-only audit sequence
1. Resolve the target safely:
   - Confirm host/IP from 1Password or user-provided data.
   - SSH with `StrictHostKeyChecking=accept-new` and a dedicated known_hosts file when possible.
2. Identify stack:
   - `hostname`, `/etc/os-release`
   - `dpkg-query -W 'hestia*' 'roundcube*' 'php*-fpm' 'php*-mysql' 'nginx*'`
   - `systemctl is-active nginx php*-fpm dovecot exim4 mariadb`
3. Inspect Hestia/Vesta webmail state:
   - `/usr/local/hestia/bin/v-list-sys-webmail plain`
   - `grep -En '^(WEBMAIL_ALIAS|WEBMAIL_SYSTEM|DB_SYSTEM|WEB_SYSTEM|PROXY_SYSTEM|IMAP_SYSTEM|MAIL_SYSTEM)=' /usr/local/hestia/conf/hestia.conf /etc/hestiacp/hestia.conf`
   - `/usr/local/hestia/bin/v-list-mail-domain <user> <domain> json`
4. Inspect Nginx routing:
   - `/etc/nginx/conf.d/domains/` symlinks for `mail.domain.com` and `webmail.domain.com`
   - Generated configs under `/home/<user>/conf/mail/<domain>/` and `/home/<user>/conf/web/mail.<domain>/`
   - Avoid hand-inserting `location` blocks globally; Hestia generates per-domain webmail configs.
5. Inspect Roundcube:
   - `/etc/roundcube/config.inc.php` sanitized only
   - `/var/lib/roundcube/`, `/var/log/roundcube/`, `/var/lib/roundcube/logs/`
   - `des_key` must not remain `%des_key%`
   - DB DSN must parse, but never print the password.
6. Probe externally and locally:
   - `curl -sSI https://mail.domain.com/`
   - `curl -fsSL https://mail.domain.com/ | grep -Eio 'Roundcube Webmail|name="_user"|name="_pass"'`
   - DNS: `mail.domain.com` should be DNS-only in Cloudflare, not proxied.

## Preferred repair path: use Hestia’s own webmail commands
For Hestia 1.9+ with Roundcube installed, prefer the official command path over manual Nginx includes:

```bash
export PATH=/usr/local/hestia/bin:$PATH
v-change-sys-config-value WEBMAIL_SYSTEM roundcube
v-change-sys-config-value WEBMAIL_ALIAS mail
v-add-mail-domain-webmail <user> <domain> roundcube no yes
nginx -t
php-fpm<VERSION> -t
systemctl reload php<VERSION>-fpm
systemctl reload nginx
```

Why `WEBMAIL_ALIAS=mail` often wins:
- Mail domains usually already have a valid SSL cert for `mail.domain.com`.
- `webmail.domain.com` may exist in Cloudflare but lack a matching certificate on the VPS.
- Hestia’s generated config for `mail.domain.com` serves Roundcube cleanly at `/`.

If the business explicitly wants `webmail.domain.com`, verify or issue a cert covering `webmail.domain.com` first; otherwise use `mail.domain.com` as the canonical browser URL.

## Common Hestia/Roundcube failure ladder
Handle blockers in order; each fix may reveal the next real error.

### 1. URL returns Hestia/default page or 404
Likely webmail not enabled for the mail domain.

Checks:
- `WEBMAIL_SYSTEM` empty in Hestia config
- mail domain JSON has `WEBMAIL` empty
- symlink points to `/home/<user>/conf/web/mail.<domain>/...` instead of `/home/<user>/conf/mail/<domain>/...`

Fix:
- Set `WEBMAIL_SYSTEM=roundcube`, `WEBMAIL_ALIAS=mail`
- Run `v-add-mail-domain-webmail <user> <domain> roundcube no yes`

### 2. 500 with `open_basedir restriction` after manual include
Likely someone inserted a Roundcube `location` include into a normal web-domain PHP pool.

Safer correction:
- Stop hand-routing `/var/lib/roundcube` through the user web pool.
- Restore/use Hestia-generated mail-domain webmail config, which uses `/run/php/www.sock` running as `hestiamail`.

### 3. Roundcube `des_key` still `%des_key%`
Roundcube install was incomplete or config was copied without post-install substitution.

Fix:
```bash
RC_DES_KEY=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-24)
python3 - "$RC_DES_KEY" <<'PY'
import sys, pathlib
key=sys.argv[1]
p=pathlib.Path('/etc/roundcube/config.inc.php')
p.write_text(p.read_text().replace('%des_key%', key))
PY
```

### 4. Fatal `Undefined constant PDO::MYSQL_ATTR_FOUND_ROWS`
`pdo_mysql` is missing from the active PHP version.

Fix with approval because it changes system packages:
```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y php<VERSION>-mysql
phpenmod -v <VERSION> pdo_mysql mysqli mysqlnd || true
php-fpm<VERSION> -t
systemctl reload php<VERSION>-fpm
```

Note: package install may upgrade sibling PHP packages. Mention that in the final report.

### 5. DB Error `Access denied for user 'roundcube'@'localhost'` or DB missing
Hestia/Roundcube files exist but the Roundcube DB/user/schema were not created.

Checks:
```bash
mysql -NBe "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='roundcube';"
mysql -NBe "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='roundcube';"
mysql -NBe "SELECT COUNT(*) FROM mysql.user WHERE User='roundcube' AND Host='localhost';"
```

Fix with double-confirm because it creates DB credentials:
- Parse existing password from `/etc/roundcube/config.inc.php` internally.
- Create DB/user using that password.
- Import `/var/lib/roundcube/SQL/mysql.initial.sql`.
- Do not print the password or full DSN.

## Final validation checklist
Before declaring success:

- `nginx -t` passes.
- `php-fpm<VERSION> -t` passes.
- `systemctl is-active nginx php<VERSION>-fpm dovecot exim4 mariadb` all active.
- Public HTTPS URL returns HTTP 200 without `-k`.
- HTML contains `Roundcube Webmail`, `name="_user"`, and `name="_pass"`.
- TLS validates for the chosen hostname.
- Roundcube DB exists and has tables.
- Recent Roundcube/Nginx logs show no new errors after the final probe.
- Report the canonical URL and explicitly say which URLs are not canonical if relevant.

## References
- `references/hestia-roundcube-webmail-repair-2026-06-28.md` — session-specific repair path for `marketingdigitalad.com` on Hestia 1.9.6, including error ladder and validations.
