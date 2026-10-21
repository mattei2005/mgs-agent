# PHP emergency patch — approved scope completed

## Authority

- Initial patch confirmation: Rodolfo, message `1562585423589412987`.
- Exact socket-isolation and service recovery confirmation: Rodolfo, message `1562594110655828149`.
- Current hosting clarification: Rodolfo, message `1562595243084484661`.
- Origin thread: `1562582544292249772`.

## Outcome

MatteiInc01, MatteiInc02 and MatteiInc03JBF each have all 21 approved PHP 8.3 core packages at `8.3.36-1+ubuntu22.04+1`, upgraded from `8.3.33-1+ubuntu22.04+1`. All four approved local agent-VPS CLI packages are now `8.3.6-0ubuntu0.24.04.13`, upgraded from `.12`. The installed Ubuntu changelog explicitly includes both CVE-2026-109618 and CVE-2026-109619. Total: 67 package upgrades across the four approved hosts.

## Socket incident and recovery

The initial authorized PHP-FPM restart on Inc01 exposed a pre-existing collision: the unused PHP pool listened on `/var/run/mgs-finance-dash.sock`, identical to the Node/systemd application's `/run/mgs-finance-dash.sock`. This caused the finance dashboard to return 502. The completed PHP patch was retained.

After the separate confirmation, exactly these references were changed to `/var/run/mgs-finance-dash-php.sock`:

- `/etc/php83rc/fpm.d/mgs-finance-dash.conf`
- `/etc/nginx-rc/conf.d/mgs-finance-dash.d/proxy.conf`

Both exact pre-state hashes matched the frozen plan. Backups were taken, FPM and Nginx config tests passed, the finance service/socket were stopped together, FPM was restarted, finance socket/service started and Nginx reloaded. Live listeners now show PHP-FPM on the isolated `-php.sock` and Node/systemd on the original application socket. Public dashboard HTTP200 and browser navigation to the rendered `/login` form passed. Direct-origin access remains denied403 as designed. Database-service PIDs, Apache and Nginx master PID were unchanged. No financial mutation endpoints, application code, authentication settings or credentials were modified. Authenticated financial views were not exercised; this is infrastructure recovery evidence, not a fresh financial audit.

## Final validation

- 110 mapped applications: 75 on Inc01, 15 on Inc02, 20 on Inc03.
- 220 final HTTP checks covering public and origin requests, compared with the pre-update baseline. Origin-only TLS bypass is diagnostic, not certificate-validating public proof.
- 109 direct FastCGI PHP executions completed without fatal/error regression. The one skipped pool belongs to the Node finance application, which has no index.php and was tested by HTTP/browser instead.
- No remaining regressions against the pre-update baseline, no deleted/old PHP processes, unchanged PHP module sets and no unapproved configuration differences.
- Nginx/PHP configuration tests and dpkg audit clean. Original rollback hashes revalidated.
- Zeus, Atena and Ares gateway PIDs unchanged during the local CLI transaction; no reboot marker and no gateway restart.

Pre-existing public limitations remain: 403 on allincraft.com, kievportal.com, portalbrasilnews.com and prospecthomeimprovement.com; missing DNS for bkp2.ducapes.com. The finance dashboard's direct-origin403 is an intentional access guard, not an outage. These conditions predated the patch and were not altered under this scope.

## Recovery material

Each RunCloud host retains 21 verified original previous-version .deb packages and a private PHP/Nginx config archive under `/root/zeus-php-security-20261021-1562585423589412987`. Inc01 also has exact two-file pre-repair backups and recovery receipts in its `socket-recovery-1562594110655828149` subdirectory.

The local CLI host retains four verified previous-version .deb packages and CLI configuration backup under `/root/.hermes/secure-backups/vps-maintenance/php-security-20261021-1562585423589412987`.

The exercised executors, transport receipts and aggregate `completion.json` are preserved beside this report. No retention/deletion scope was added.

## Additional emails and current provider scope

The Malwarebytes image and two DigitalOcean images describe the same PHP2Shell incident, not additional distinct vulnerabilities. Useful guidance: require installed rather than merely scheduled fixes, include CMS/admin panels/embedded PHP in inventory and do not substitute WAF/temporary settings for the patch. A generic DigitalOcean notice does not prove a current MGS DigitalOcean workload or compromise.

Rodolfo confirmed current hosting is Hetzner with RunCloud and Hostinger only. That statement is persisted in `context/sites.md`, registry key `infrastructure.hosting.providers`. Historical AWS/Bitnami/DigitalOcean references are not current-hosting evidence; no account closure, deletion or billing change is inferred.

This completion covers only the three named Mattei hosts and local agent VPS. Other Hetzner/Hostinger hosts, dormant runtimes and other embedded PHP installations are not automatically certified. Future RunCloud configuration regeneration must revalidate socket separation; the exercised current repair does not guarantee preservation by a future provider rebuild.
