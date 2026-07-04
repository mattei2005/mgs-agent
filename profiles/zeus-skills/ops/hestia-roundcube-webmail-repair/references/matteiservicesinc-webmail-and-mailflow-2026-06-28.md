# matteiservicesinc.com / marketingdigitalad.com — Hestia Roundcube + Mail Flow Lessons

## Context

Two domains on the same Hestia VPS (`188.34.183.6`, `server.boostingecon.com`) clarified two distinct classes of problems:

1. `marketingdigitalad.com` — Roundcube interface was repaired, but the domain intentionally remains hosted at Zoho for mail routing.
2. `matteiservicesinc.com` — domain was already intended to be 100% on Hestia; only its webmail interface was not wired to the official Hestia Roundcube mail-domain config.

## Durable Lessons

### 1. Webmail repair and mail routing are separate

A working Roundcube URL proves only browser UI + IMAP login path. It does not prove internet mail routing.

Check DNS before saying send/receive is solved:

```bash
dig +short MX DOMAIN
dig +short TXT DOMAIN
dig +short TXT mail._domainkey.DOMAIN
dig +short TXT _dmarc.DOMAIN
```

If MX points to Zoho, incoming mail goes to Zoho even if Hestia has mailboxes and Roundcube.

If SPF authorizes Zoho only, VPS-originated mail can be rejected by Gmail with `550-5.7.26 Gmail requires all senders to authenticate with either SPF or DKIM`.

### 2. Existing `mail.domain.com` web domain can mask webmail

For `matteiservicesinc.com`, DNS was already correct and account `mgs@matteiservicesinc.com` existed, but Hestia mail domain had `WEBMAIL` empty and Nginx symlinks still pointed to the old web-domain config:

```text
/etc/nginx/conf.d/domains/mail.matteiservicesinc.com.conf -> /home/USER/conf/web/mail.matteiservicesinc.com/nginx.conf
```

The fix was not DNS. It was regenerating the official Hestia webmail config:

```bash
export PATH=/usr/local/hestia/bin:$PATH
v-add-mail-domain-webmail USER DOMAIN roundcube no yes
nginx -t
php-fpm8.3 -t
systemctl reload nginx
systemctl reload php8.3-fpm
```

Expected symlinks after fix:

```text
/etc/nginx/conf.d/domains/mail.DOMAIN.conf     -> /home/USER/conf/mail/DOMAIN/nginx.conf
/etc/nginx/conf.d/domains/mail.DOMAIN.ssl.conf -> /home/USER/conf/mail/DOMAIN/nginx.ssl.conf
```

Expected Hestia state:

```text
WEBMAIL_ALIAS = mail.DOMAIN
WEBMAIL       = roundcube
```

### 3. Cloudflare target for full Hestia-hosted mail

For a domain that should be 100% Hestia-hosted:

```text
A     mail                  VPS_IP                                  DNS only
MX    @                     mail.DOMAIN                             priority 10
TXT   @                     v=spf1 mx a:mail.DOMAIN ~all
TXT   mail._domainkey       v=DKIM1; k=rsa; p=<Hestia public key>
TXT   _dmarc                v=DMARC1; p=none; rua=mailto:postmaster@DOMAIN
```

If DMARC policy is already stricter (`quarantine`/`reject`), do not loosen it automatically. Report the current policy and only change with explicit approval.

### 4. `webmail.domain.com` is optional

Prefer `https://mail.DOMAIN` as canonical because Hestia's `WEBMAIL_ALIAS=mail` and SSL cert commonly cover `mail.DOMAIN`.

`webmail.DOMAIN` can be added as CNAME/A only if DNS and cert coverage are known. Do not require it for the webmail repair.

## Validation Evidence Pattern

After repair, validate with:

```bash
curl -fsSI https://mail.DOMAIN/
curl -fsSL https://mail.DOMAIN/ | grep -Eio 'Roundcube Webmail|name="_user"|name="_pass"'
systemctl is-active nginx php8.3-fpm dovecot exim4 mariadb
```

Then inspect recent logs for new errors; old pre-fix Roundcube errors can remain in the tail, so correlate by timestamp.
