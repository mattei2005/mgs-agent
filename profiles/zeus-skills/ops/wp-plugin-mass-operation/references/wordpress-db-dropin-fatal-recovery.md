# WordPress `db.php` Drop-in Fatal Recovery

Use this branch when `/wp-admin/` returns the generic WordPress critical-error page after plugin maintenance and the failure persists after normal plugins are isolated.

## Diagnostic boundary

1. Prove the public symptom independently: capture status and critical-error marker for `/wp-admin/`, homepage and REST.
2. Preserve and restore the exact normal-plugin activation baseline during isolation. If `/wp-admin/` still fails with all normal plugins inactive, inspect `wp-content` drop-ins and mu-plugins before blaming a theme or core.
3. Trigger one fresh failing request and inspect a bounded tail of the site-specific Nginx/FastCGI error log. Reduce output to exact fatal class, file and line; never dump arbitrary logs.
4. Enumerate and lint `wp-content/db.php`, `advanced-cache.php`, `object-cache.php`, other recognized drop-ins and mu-plugins. Run core checksum and database checks separately.
5. Remember that `wp-content/db.php` loads very early. Calling later WordPress helpers such as `wp_kses()` from an error branch can itself produce a fatal before the admin redirect or dashboard bootstrap.

## Orphan cache drop-in branch

When the dashboard reports that W3 Total Cache files are missing and specifically names `wp-content/object-cache.php`:

1. Prove whether the `w3-total-cache` plugin directory and normal-plugin entry are absent. Do not reinstall a plugin that was intentionally inactive/removed merely to silence its orphan drop-in.
2. Inspect the drop-in for W3 Total Cache provenance markers without dumping arbitrary source or secrets.
3. Preserve and hash `object-cache.php` outside the webroot, then move the live file out of `wp-content` reversibly.
4. Require `wp_using_ext_object_cache() === false`, unchanged normal/active plugin counts, database/core checks and public/admin/REST smoke tests before keeping the repair.
5. Do not leave `.disabled`, `.bak` or other source-bearing PHP backups inside the webroot.

## Reversible repair

1. Require the normal production authorization and any Critical confirmation needed for temporary SSH credential creation.
2. Hash and preserve the exact failing drop-in outside the webroot under a protected backup family. Require a second hash readback and restrictive owner/mode.
3. Move the live drop-in out of `wp-content`; do not delete it and do not leave a renamed PHP backup inside the webroot, where a server may expose source.
4. Immediately validate:
   - `/wp-admin/` reaches login/dashboard without the critical marker;
   - homepage and REST return 200;
   - `wp db check` passes;
   - core checksum passes;
   - normal active-plugin count equals the preflight baseline.
5. Roll back the move on any failed gate. Do not restart PHP/Nginx merely by habit; reload only when live evidence shows OPcache/service state still prevents the repaired path from taking effect.
6. Revoke the temporary SSH credential in `finally`, prove API list zero, prove the same key can no longer authenticate and remove local private material.

## Reporting

Report the confirmed component and line, but do not attribute causality to a named plugin update unless logs, package provenance or a canonical event proves it. Record the protected rollback path, hash, public/admin/REST checks, database/core checks, active-plugin baseline and zero-credential readback.
