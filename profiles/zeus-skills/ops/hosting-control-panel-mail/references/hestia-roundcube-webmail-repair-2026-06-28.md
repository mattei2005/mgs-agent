# Hestia/Roundcube Webmail Repair — marketingdigitalad.com — 2026-06-28

## Context
Rodolfo needed browser webmail access for a Hetzner VPS running Hestia/Vesta-style mail hosting. IMAP/SMTP worked in desktop clients, but none of these opened a usable browser interface:

- `https://webmail.marketingdigitalad.com`
- `https://mail.marketingdigitalad.com`
- `https://marketingdigitalad.com/webmail`
- `https://mail.marketingdigitalad.com/roundcube`

Relevant facts:
- VPS: `188.34.183.6`, hostname `server.boostingecon.com`
- Hestia user: `rodloguda`
- Domain: `marketingdigitalad.com`
- Mail account tested: `mgs@marketingdigitalad.com`
- DNS in Cloudflare had `mail.marketingdigitalad.com` and `webmail.marketingdigitalad.com` A records pointing to `188.34.183.6`, DNS-only.

## Initial state observed
- Hestia package present: `hestia 1.9.6`
- Ubuntu: 24.04
- Services active: `nginx`, `php8.3-fpm`, `dovecot`, `exim4`, `mariadb`
- `/usr/local/hestia/conf/hestia.conf` had:
  - `WEBMAIL_ALIAS=''`
  - `WEBMAIL_SYSTEM=''`
  - `DB_SYSTEM='mysql'`
- Mail domain JSON showed:
  - `WEBMAIL_ALIAS` malformed/empty in earlier state
  - `WEBMAIL` empty
  - SSL/LE enabled for mail domain
- Nginx symlinks initially pointed `mail.marketingdigitalad.com` to the normal web-domain config under `/home/rodloguda/conf/web/mail.marketingdigitalad.com/`.
- The manual include attempt routed Roundcube through the wrong PHP-FPM pool and caused `open_basedir` errors.

## Error ladder

### 1. 404/no webmail route
`curl -I http://188.34.183.6/webmail` returned 404. Roundcube was present on disk, but Hestia had no active webmail system and no generated mail-domain webmail config.

### 2. Manual Nginx include caused wrong execution context
Manual `include /etc/nginx/conf.d/roundcube.inc*;` inside `/home/rodloguda/conf/web/mail.marketingdigitalad.com/nginx.conf` used the domain web PHP pool:

`/run/php/php8.3-fpm-mail.marketingdigitalad.com.sock`

That pool ran under `rodloguda` with open_basedir limited to the web domain, causing:

`open_basedir restriction in effect. File(/var/lib/roundcube/...) is not within the allowed path(s)`

Lesson: do not hand-route Roundcube through a normal user web pool. Use Hestia’s generated mail-domain webmail config, which uses `/run/php/www.sock` and `hestiamail`.

### 3. Roundcube config placeholder
`/etc/roundcube/config.inc.php` still had:

`$config["des_key"] = "%des_key%";`

This indicates incomplete Hestia Roundcube post-install/config generation.

### 4. Missing `pdo_mysql`
After Hestia webmail routing was corrected, Roundcube hit:

`PHP Fatal error: Undefined constant PDO::MYSQL_ATTR_FOUND_ROWS`

Cause: active PHP 8.3 lacked `php8.3-mysql` / `pdo_mysql`.

Fix required package install approval. Installing `php8.3-mysql` also upgraded sibling PHP 8.3 packages from 8.3.30 to 8.3.31 on that server.

### 5. Missing Roundcube DB/user/schema
After PHP MySQL module was enabled, Roundcube hit:

`DB Error: SQLSTATE[HY000] [1045] Access denied for user 'roundcube'@'localhost'`

Checks showed:
- `roundcube` database did not exist
- `roundcube` MySQL user did not exist
- 0 Roundcube tables

Fix required DB credential creation approval. The password was parsed internally from `/etc/roundcube/config.inc.php`; it was never printed.

## Repair sequence that worked

### Backups
Created timestamped backups under `/root/zeus-webmail-fix-<timestamp>/` and `/root/zeus-webmail-db-fix-<timestamp>/`, including:

- `/usr/local/hestia/conf/hestia.conf`
- `/etc/roundcube/config.inc.php`
- affected Nginx configs/symlink metadata
- mail domain config directory

### Hestia webmail activation
```bash
export PATH=/usr/local/hestia/bin:$PATH
v-change-sys-config-value WEBMAIL_SYSTEM roundcube
v-change-sys-config-value WEBMAIL_ALIAS mail
v-add-mail-domain-webmail rodloguda marketingdigitalad.com roundcube no yes
nginx -t
php-fpm8.3 -t
systemctl reload nginx
systemctl reload php8.3-fpm
```

Result:
- Hestia config:
  - `WEBMAIL_ALIAS='mail'`
  - `WEBMAIL_SYSTEM='roundcube'`
- Mail domain:
  - `WEBMAIL_ALIAS=mail.marketingdigitalad.com`
  - `WEBMAIL=roundcube`
- Symlinks:
  - `/etc/nginx/conf.d/domains/mail.marketingdigitalad.com.conf -> /home/rodloguda/conf/mail/marketingdigitalad.com/nginx.conf`
  - `.ssl.conf -> /home/rodloguda/conf/mail/marketingdigitalad.com/nginx.ssl.conf`

### Roundcube `des_key`
```bash
RC_DES_KEY=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-24)
python3 - "$RC_DES_KEY" <<'PY'
import sys, pathlib
key=sys.argv[1]
p=pathlib.Path('/etc/roundcube/config.inc.php')
p.write_text(p.read_text().replace('%des_key%', key))
PY
```

### PHP MySQL driver
```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y php8.3-mysql
phpenmod -v 8.3 pdo_mysql mysqli mysqlnd || true
php-fpm8.3 -t
systemctl reload php8.3-fpm
```

Validation after install:
- `php -m` showed `mysqli`, `mysqlnd`, `PDO`, `pdo_mysql`
- `php8.3-fpm` active

### Roundcube DB/user/schema
Password was parsed internally from config and used to create the DB user without printing secrets.

Operations:
- `CREATE DATABASE IF NOT EXISTS roundcube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- `CREATE USER IF NOT EXISTS 'roundcube'@'localhost' IDENTIFIED BY <config password>;`
- `ALTER USER 'roundcube'@'localhost' IDENTIFIED BY <config password>;`
- grant all privileges on `roundcube.*`
- import `/var/lib/roundcube/SQL/mysql.initial.sql`

Validation:
- DB exists: `1`
- Roundcube tables: `17`
- user exists: `1`
- schema version: `2022081200`

## Final validation
Public checks:

- `https://mail.marketingdigitalad.com/` -> HTTP 200
- `http://mail.marketingdigitalad.com/` -> 301 to HTTPS
- TLS validates for `mail.marketingdigitalad.com`
- HTML markers found:
  - `<title>Roundcube Webmail :: Welcome to Roundcube Webmail`
  - `name="_user"`
  - `name="_pass"`

Service checks:
- `nginx`, `php8.3-fpm`, `dovecot`, `exim4`, `mariadb` all active.

Log check:
- No new Roundcube errors after final successful probe.

## Final user-facing answer shape
Keep the answer short and operational:

- Canonical URL: `https://mail.marketingdigitalad.com`
- Login: full e-mail address + mailbox password
- State fixed: Roundcube enabled through Hestia, PHP MySQL enabled, DB/schema created
- Validation evidence: HTTP 200, Roundcube login markers, TLS OK, services active
- Note that `webmail.marketingdigitalad.com` is not canonical unless a matching SSL cert/config is added.

## Durable lessons
- If Hestia/Vesta has `WEBMAIL_SYSTEM` empty, fix the control-panel webmail state first; do not pile manual Nginx includes into user web configs.
- `open_basedir` errors after adding Roundcube include usually mean the request is going through the wrong PHP pool.
- Hestia’s Roundcube webmail normally belongs under `/home/<user>/conf/mail/<domain>/` generated configs, not `/home/<user>/conf/web/mail.<domain>/` configs.
- A 500 can be a ladder: route -> config placeholder -> PHP module -> DB credentials/schema. Fix and re-probe one layer at a time.
- Use the hostname with the valid cert as canonical. For this case, `mail.marketingdigitalad.com` was correct; `webmail.marketingdigitalad.com` had DNS but not the working Hestia/cert endpoint.
