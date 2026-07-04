---
name: hestia-roundcube-webmail-repair
description: Use when repairing or enabling Roundcube webmail on a Hestia/Vesta-style VPS, especially when mailboxes work in Outlook/Thunderbird but the browser webmail URL returns 404/500. Covers safe SSH/1Password access, Hestia WEBMAIL_SYSTEM/WEBMAIL_ALIAS, Roundcube config, PHP MySQL driver, Roundcube DB schema, Nginx/PHP-FPM validation, and DNS/MX pitfalls.
version: 1.0.0
author: Zeus MGS
license: Proprietary-MGS
metadata:
  hermes:
    tags: [mgs, hestia, roundcube, webmail, vps, email, nginx, php-fpm, mysql]
    related_skills: [discord-ops]
---

# Hestia Roundcube Webmail Repair

## Overview

Use this skill when a Hestia/Vesta-style VPS has working mail accounts at IMAP/SMTP level, but no usable browser webmail interface. The common symptom is: Hestia shows mail domains/accounts, DNS has `mail.domain.com`, Outlook/eM Client can be configured, but `https://mail.domain.com`, `https://webmail.domain.com`, or `/webmail` returns 404/500.

This workflow is based on the MGS repair of `marketingdigitalad.com` on a Hetzner VPS (`server.boostingecon.com`, Hestia 1.9.x, Ubuntu 24.04), where Roundcube existed but Hestia had incomplete webmail configuration.

Security rule: never print or paste passwords/tokens/application passwords in chat. Pull VPS credentials from 1Password internally and report only item name + sanitized lengths/validation.

## When to Use

- Hestia/Vesta mail account exists, but user asks for webmail URL.
- `mail.domain.com` opens a placeholder/default page instead of Roundcube.
- `/webmail` returns 404.
- Roundcube returns 500 with Nginx/FastCGI errors.
- Logs mention `open_basedir`, `%des_key%`, `PDO::MYSQL_ATTR_FOUND_ROWS`, or Roundcube DB access denied.

Do not use this for:
- Zoho/Google Workspace hosted mail unless the goal is to migrate MX to the VPS.
- DNS-only investigation with no VPS access.
- Password resets unless explicitly approved; altering passwords is a critical operation.

## Required Confirmations

AGENT.md critical subset applies:

- Editing `/etc`, `/usr`, PHP-FPM pools, Nginx configs, package installs, and DB credentials require confirmation if not already explicitly requested.
- Creating/changing MySQL users/passwords always requires double-confirm.
- Do not delete files. Backup before edits.

## Fast Diagnosis

From local Zeus shell, load 1Password without exposing secrets:

```bash
set -a
source /root/mgs-agent/.env 2>/dev/null || true
set +a
op item list --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --format json \
  | jq -r '.[] | select((.title|ascii_downcase)|test("email vps|hestia|vps")) | [.title,.id] | @tsv'
```

SSH using the item fields internally. Sanitize output:

```bash
ITEM='Email VPS MSG'
URL=$(op item get "$ITEM" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields label='admin console URL' --reveal)
USER=$(op item get "$ITEM" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields label='admin console username' --reveal)
PASS=$(op item get "$ITEM" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields label='console password' --reveal)
HOST=$(printf '%s\n' "$URL" | awk '{print $NF}' | sed 's/^.*@//')
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs "$USER@$HOST" 'hostname; date -Is'
```

On the VPS:

```bash
export PATH=/usr/local/hestia/bin:$PATH
hostname
cat /etc/os-release | grep -E '^(PRETTY_NAME|VERSION_CODENAME)='
systemctl is-active nginx php8.3-fpm dovecot exim4 mariadb 2>/dev/null || true
grep -En '^(WEBMAIL_ALIAS|WEBMAIL_SYSTEM|DB_SYSTEM|WEB_SYSTEM|IMAP_SYSTEM|MAIL_SYSTEM)=' \
  /usr/local/hestia/conf/hestia.conf /etc/hestiacp/hestia.conf 2>/dev/null || true
v-list-sys-webmail plain 2>&1 || true
v-list-mail-domain USER DOMAIN json | jq .
```

Probe externally:

```bash
curl -sSI --max-time 12 https://mail.DOMAIN/
curl -sSI --max-time 12 http://mail.DOMAIN/
curl -sSI --max-time 12 http://webmail.DOMAIN/
```

## Known Failure Patterns and Fixes

### 1. Hestia has webmail disabled

Symptoms:

```text
WEBMAIL_ALIAS=''
WEBMAIL_SYSTEM=''
v-list-sys-webmail plain -> empty
mail domain WEBMAIL is empty
```

Fix after confirmation:

```bash
export PATH=/usr/local/hestia/bin:$PATH
v-change-sys-config-value WEBMAIL_SYSTEM roundcube
v-change-sys-config-value WEBMAIL_ALIAS mail
v-add-mail-domain-webmail USER DOMAIN roundcube no yes
nginx -t
php-fpm8.3 -t
systemctl reload nginx
systemctl reload php8.3-fpm
```

Prefer `WEBMAIL_ALIAS=mail` when the SSL certificate already covers `mail.domain.com`. Do not force `webmail.domain.com` unless DNS and SSL are ready for that hostname.

### 2. Manual `/webmail` include causes `open_basedir` errors

Symptoms in `/var/log/nginx/error.log` or domain error log:

```text
open_basedir restriction in effect
Unable to open primary script: /var/lib/roundcube/public_html/index.php
```

Cause: Roundcube was included into a normal user website PHP-FPM pool (`/run/php/php8.3-fpm-mail.domain.com.sock`) instead of the Hestia webmail template using `/run/php/www.sock` under `hestiamail`.

Preferred fix: stop patching random `roundcube.inc` into the web domain and regenerate official mail-domain webmail config with `v-add-mail-domain-webmail`.

Validate symlinks point to mail-domain config:

```bash
ls -l /etc/nginx/conf.d/domains/mail.DOMAIN.conf /etc/nginx/conf.d/domains/mail.DOMAIN.ssl.conf
# Expected target: /home/USER/conf/mail/DOMAIN/nginx(.ssl).conf
```

### 3. Roundcube `des_key` still placeholder

Symptoms:

```bash
grep -n '%des_key%' /etc/roundcube/config.inc.php
```

Fix after backup:

```bash
cp -a /etc/roundcube/config.inc.php /root/roundcube-config.inc.php.bak.$(date +%F-%H%M%S)
RC_DES_KEY=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-24)
python3 - "$RC_DES_KEY" <<'PY'
import sys, pathlib
key=sys.argv[1]
p=pathlib.Path('/etc/roundcube/config.inc.php')
s=p.read_text().replace('%des_key%', key)
p.write_text(s)
PY
```

Never print the generated key.

### 4. Missing PHP MySQL driver

Symptoms in `/var/lib/roundcube/logs/errors.log`:

```text
Undefined constant PDO::MYSQL_ATTR_FOUND_ROWS
PDO drivers =>
```

Fix after confirmation because this modifies system packages:

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq php8.3-mysql
phpenmod -v 8.3 pdo_mysql mysqli mysqlnd >/dev/null 2>&1 || true
php-fpm8.3 -t
nginx -t
systemctl reload php8.3-fpm
systemctl reload nginx
php -m | grep -Ei 'pdo|mysql|mysqli'
php-fpm8.3 -i | grep -Ei 'PDO drivers|pdo_mysql|mysqlnd' | head
```

Pitfall: apt can update other installed PHP 8.3 packages at the same time. Watch for dpkg conffile prompts and keep local config unless there is an explicit reason to replace it.

### 5. Roundcube DB/user missing

Symptoms:

```text
DB Error: SQLSTATE[HY000] [1045] Access denied for user 'roundcube'@'localhost'
SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='roundcube'; -> 0
mysql.user has no roundcube@localhost
```

Fix after critical confirmation; use the password already in `/etc/roundcube/config.inc.php`, do not invent a new one unless explicitly resetting credentials:

```bash
SQL_FILE=$(mktemp)
chmod 600 "$SQL_FILE"
python3 - <<'PY' > "$SQL_FILE"
import re, pathlib, urllib.parse
s=pathlib.Path('/etc/roundcube/config.inc.php').read_text()
m=re.search(r'\$config\[["\']db_dsnw["\']\]\s*=\s*["\']([^"\']+)', s)
if not m:
    raise SystemExit('db_dsnw not found')
p=urllib.parse.urlparse(m.group(1))
user=urllib.parse.unquote(p.username or '')
password=urllib.parse.unquote(p.password or '')
db=(p.path or '/roundcube').lstrip('/')
if user!='roundcube' or db!='roundcube' or not password:
    raise SystemExit('unexpected db dsn')
def q(v): return "'" + v.replace('\\','\\\\').replace("'","''") + "'"
print("CREATE DATABASE IF NOT EXISTS `roundcube` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
print("CREATE USER IF NOT EXISTS 'roundcube'@'localhost' IDENTIFIED BY " + q(password) + ";")
print("ALTER USER 'roundcube'@'localhost' IDENTIFIED BY " + q(password) + ";")
print("GRANT ALL PRIVILEGES ON `roundcube`.* TO 'roundcube'@'localhost';")
print("FLUSH PRIVILEGES;")
PY
mysql < "$SQL_FILE"
rm -f "$SQL_FILE"
mysql roundcube < /var/lib/roundcube/SQL/mysql.initial.sql
systemctl reload php8.3-fpm
systemctl reload nginx
```

Validate:

```bash
mysql -NBe "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='roundcube';"
mysql -NBe "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='roundcube';"
mysql -NBe "SELECT value FROM roundcube.system WHERE name='roundcube-version';"
```

### 6. Existing `mail.domain.com` web domain masks Roundcube

Symptoms:

```text
v-list-mail-domain USER DOMAIN json -> WEBMAIL empty
/etc/nginx/conf.d/domains/mail.DOMAIN.conf -> /home/USER/conf/web/mail.DOMAIN/nginx.conf
https://mail.DOMAIN/ returns HTTP 200 but not Roundcube
```

Cause: `mail.DOMAIN` exists as a normal web domain/subdomain and Nginx routes to `/conf/web/...` instead of Hestia's mail-domain webmail config.

Fix after confirmation:

```bash
export PATH=/usr/local/hestia/bin:$PATH
v-add-mail-domain-webmail USER DOMAIN roundcube no yes
nginx -t
php-fpm8.3 -t
systemctl reload nginx
systemctl reload php8.3-fpm
```

Validate symlinks changed to `/conf/mail/DOMAIN/`:

```bash
ls -l /etc/nginx/conf.d/domains/mail.DOMAIN.conf /etc/nginx/conf.d/domains/mail.DOMAIN.ssl.conf
```

Expected target:

```text
/home/USER/conf/mail/DOMAIN/nginx.conf
/home/USER/conf/mail/DOMAIN/nginx.ssl.conf
```

## Mail Flow Pitfall: Webmail Is Not Mail Routing

Fixing Roundcube only fixes the browser interface. Sending/receiving can still fail because of DNS and mail routing.

Session-specific reference: `references/matteiservicesinc-webmail-and-mailflow-2026-06-28.md` captures the `marketingdigitalad.com` vs `matteiservicesinc.com` distinction: Zoho-hosted MX/SPF can make Roundcube work while Gmail rejects VPS mail, while a fully Hestia-hosted domain may only need `v-add-mail-domain-webmail` to repoint `mail.domain.com` from `/conf/web/...` to `/conf/mail/...`.

Check DNS:

```bash
dig +short A mail.DOMAIN
dig +short MX DOMAIN
dig +short TXT DOMAIN
dig +short TXT _dmarc.DOMAIN
```

If MX still points to Zoho (`mx.zoho.com`, `mx2.zoho.com`, `mx3.zoho.com`), inbound mail will go to Zoho, not the Hestia VPS. The Hestia mailbox can exist and webmail can work, but internet mail will not arrive there.

For Hestia-hosted mail, Cloudflare DNS usually needs:

```text
A     mail.DOMAIN       VPS_IP       DNS only
MX    DOMAIN            mail.DOMAIN  priority 10
TXT   DOMAIN            v=spf1 mx a:mail.DOMAIN ~all
TXT   _dmarc.DOMAIN     v=DMARC1; p=none; rua=mailto:postmaster@DOMAIN
TXT   <dkim selector>   Hestia DKIM value
```

Do not change DNS without explicit approval. DNS changes can break existing Zoho mailboxes.

## Validation Checklist

- [ ] Backups created for changed Hestia/Nginx/Roundcube files.
- [ ] `WEBMAIL_SYSTEM='roundcube'` and `WEBMAIL_ALIAS` match desired endpoint.
- [ ] Mail domain reports `WEBMAIL=roundcube`.
- [ ] Nginx symlinks point to `/home/USER/conf/mail/DOMAIN/nginx(.ssl).conf`, not `/home/USER/conf/web/mail.DOMAIN/...`.
- [ ] `nginx -t` passes.
- [ ] `php-fpm8.3 -t` passes.
- [ ] `systemctl is-active nginx php8.3-fpm dovecot exim4 mariadb` all active.
- [ ] `curl -fsSI https://mail.DOMAIN/` returns HTTP 200.
- [ ] HTML contains `Roundcube Webmail`, `name="_user"`, and `name="_pass"`.
- [ ] Roundcube logs show no new errors after final probe.
- [ ] DNS/MX reviewed separately before claiming send/receive works.

## Reporting Format

Keep the report concise:

```text
Resolvido: https://mail.DOMAIN
Validação: HTTP 200, Roundcube login form, TLS OK, services active.
Causa: WEBMAIL_SYSTEM vazio + Roundcube DB/PHP driver incompletos.
Observação: envio/recebimento depende de MX/SPF/DKIM; webmail ≠ mail routing.
```

Never include secrets, DB passwords, mailbox passwords, tokens, or full sensitive config dumps.
