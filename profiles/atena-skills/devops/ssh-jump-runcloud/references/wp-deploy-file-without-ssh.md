# WP Deploy File Without SSH — Full Workflow

> Absorbed from: `wp-deploy-file-without-ssh` skill (archived 2026-05-06)
> Use when: SSH blocked on all ports. Admin credentials + WP Plugin Editor available.

When the target WP server has SSH blocked on all ports (22, 2222, 22022, 8022)
and SFTP is unavailable, files can be deployed via the WP admin Plugin Editor
form — which writes directly to the filesystem via the WP Filesystem API.

---

## When to use

- Need to update a file on a WP server (plugin, mu-plugin, config)
- SSH/SFTP access not available or not configured
- Have admin credentials (username + **real password**, NOT Application Password)
- WP Plugin Editor is not disabled (`DISALLOW_FILE_EDIT` NOT set in wp-config.php)

---

## Critical pitfalls

### 1. Application Passwords do NOT work for form login or admin-ajax
Use the **real user password** (from 1Password) for session-based operations.

### 2. admin-ajax `edit-theme-plugin-file` — nonce expires between GET and POST
Use the **form POST instead** (step 3 below) — the form nonce lives longer.

### 3. REST `/wp/v2/plugins` POST only accepts wordpress.org slugs
Cannot upload a ZIP or arbitrary plugin. Only installs from wordpress.org.

### 4. WPS Hide Login — find the custom login URL first
Standard `wp-login.php` returns 404. Get slug from 1Password or `whl_page` option.
For eggbev: `/rodloguda/`.

### 5. Plugin activation with `die()` returns HTTP 500
If injected PHP calls `die()`, the REST activation returns 500 with empty body.
The execution still happened. Read result via WP option (bootstrap technique).

---

## Workflow — deploy a file via Plugin Editor form

**1. Login and obtain session cookies**
```python
import requests

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/115.0'
s.post(
    'https://{site}/rodloguda/',   # custom login URL
    data={
        'log': 'rodmaster',
        'pwd': PASSWORD,           # real password, NOT app password
        'wp-submit': 'Log In',
        'redirect_to': '/wp-admin/',
        'testcookie': '1'
    },
    cookies={'wordpress_test_cookie': 'WP Cookie check'},
    allow_redirects=True,
    timeout=15
)
# Success: session.url ends in /wp-admin/
```

**2. Get fresh nonce from Plugin Editor page**
```python
editor = s.get(
    'https://{site}/wp-admin/plugin-editor.php'
    '?file=simple-author-box%2Fsimple-author-box.php'
    '&plugin=simple-author-box%2Fsimple-author-box.php',
    timeout=15
)
import re
m = re.search(r'name="nonce"\s+value="([^"]+)"', editor.text)
nonce = m.group(1)
```

**3. Write file via form POST (NOT AJAX)**
```python
resp = s.post(
    'https://{site}/wp-admin/plugin-editor.php',
    data={
        'action': 'update',
        'nonce': nonce,
        'file': 'simple-author-box/simple-author-box.php',
        'plugin': 'simple-author-box/simple-author-box.php',
        'newcontent': YOUR_PHP_CONTENT,
        '_wp_http_referer': '/wp-admin/plugin-editor.php?file=simple-author-box%2Fsimple-author-box.php&plugin=simple-author-box%2Fsimple-author-box.php'
    },
    timeout=15
)
# Success: resp.url contains '?a=1' (WP redirect after successful update)
```

**4. Activate plugin via REST (Application Password works here)**
```bash
curl -s -X POST -u "$WP_USER:$APP_PASS" \
  "$WP_URL/wp-json/wp/v2/plugins/simple-author-box/simple-author-box" \
  -H "Content-Type: application/json" \
  -d '{"status":"active"}'
```
Note: Use plain slash in URL, not `%2F` — Cloudflare returns 404 for `%2F`.

**5. Restore plugin to clean state**
Repeat steps 2–3 with a clean plugin stub to leave the plugin in a safe state.

---

## Bootstrap technique — execute PHP and return data

When you need to run arbitrary PHP and retrieve the result:

1. Write PHP that stores result in a WP option:
   ```php
   <?php
   $result = do_something();
   update_option('mgs_result_key', json_encode($result));
   die();   // activation returns 500, but code ran
   ```

2. Base64-encode to avoid escaping issues:
   ```python
   import base64
   b64 = base64.b64encode(php_code.encode()).decode()
   plugin_php = f'<?php\n/** Plugin Name: Simple Author Box\n * Version: 2.5.4\n */\neval(base64_decode("{b64}"));'
   ```

3. Write + activate (activation returns 500 — expected)

4. Read result via REST settings (if registered with `show_in_rest: true`) or via
   a second bootstrap round for unregistered options.

5. Restore plugin to clean state immediately.

---

## eggbev-specific details

| Item | Value |
|------|-------|
| Admin user | `rodmaster` |
| Password source | `op item get "eggbev - WordPress" --vault "MGS Conteúdo" --fields password --reveal` |
| Custom login URL | `https://eggbev.com/rodloguda/` |
| Plugin carrier | `simple-author-box/simple-author-box.php` (inactive, safe to overwrite temporarily) |
| REST activate path | `/wp-json/wp/v2/plugins/simple-author-box/simple-author-box` (plain slash, not %2F) |
| Server IP | `162.55.28.178` (SSH blocked on all ports) |

---

## What was tried and failed (save time, don't retry)

| Approach | Result |
|----------|--------|
| SSH on port 22/2222/22022/8022 | All closed — Cloudflare proxy blocks direct SSH |
| SFTP | No SFTP credentials configured in 1Password for eggbev |
| REST `POST /wp/v2/plugins` + ZIP | Not supported — only accepts wordpress.org slugs |
| admin-ajax `edit-theme-plugin-file` | Nonce times out between GET and POST |
| WPCode REST endpoint | Not exposed via REST API |
| WP `/wp-abilities/v1/` | Read-only, no write actions available |
| WPS Hide Login + form with App Password | App Passwords rejected for form login |
