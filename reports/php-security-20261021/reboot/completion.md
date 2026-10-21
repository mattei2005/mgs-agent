# Mattei kernel reboots — 2026-10-21

Authority: critical confirmation `1562596910748139551`; later parallel-execution instruction `1562597939874893856`, thread `1562582544292249772`.

## Completed operation

- MatteiInc02 rebooted once, from kernel5.15.0-194 to5.15.0-198.
- After Rodolfo changed the execution strategy, the remaining MatteiInc01 and MatteiInc03 rebooted concurrently, each from5.15.0-187 to5.15.0-198. Inc02 was not rebooted again.
- All three have changed boot IDs, target kernel5.15.0-198-generic active, no reboot marker, no failed systemd units, active Nginx/PHP-FPM/Apache/MariaDB/cron, clean dpkg audit and correct /tmp mode/ownership. The exact package/config backups were checked before and after.
- Finance Node/socket and PostgreSQL18 started on Inc01. PHP and Node Unix sockets remained distinct after boot. Public dashboard navigation rendered the expected login form in a real browser; authenticated financial views were not exercised and no financial mutation was made.
- Application checks completed:110 mapped apps,220 public/origin HTTP checks and109 direct PHP/FastCGI executions. No regression against the previously frozen baseline. Previously disclosed public403/DNS limitations remain unchanged.
- Hostinger agent VPS boot ID and Zeus/Atena/Ares PIDs were unchanged. That VPS was not rebooted.

## Explicit health residual — not an all-green journal

The strict zero-priority-error journal predicate did not pass. Each new boot contains AMD USB/controller and audio initialization messages. Device identification on Inc02 confirms the affected PCI functions are USB/audio, not the storage or network interface. The three hardware messages are identical to Inc02's previous boot; the queried prior-boot kernel journal did not provide matching evidence for Inc01/03, so their prior existence is not asserted.

Aborted SSH key-exchange entries were also retained on Inc01/02; real authenticated SSH reads succeeded. The first Inc02 readiness collector opened and prematurely closed TCP22, which can create a kex error; it was changed to a real authenticated read-only SSH check. No blanket attribution of all aborted connections to that probe is made.

The initial Inc02 strict-journal failure remains in its historical receipt. The retry completed the application check without replaying the reboot. Reboot completion and application availability are validated independently from this unresolved strict-log predicate. No driver, firmware, SSH policy or other system configuration change was included as an incidental repair.

## Evidence

Machine-readable results, pre/post boot identities, service states, backups, diagnosis, application receipts and the actual exercised executors are preserved in this directory. Secure config archives remain under `/root/zeus-php-security-20261021-1562585423589412987/reboot-1562596910748139551` on each host.
