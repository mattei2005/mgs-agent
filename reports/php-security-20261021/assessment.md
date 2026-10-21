# PHP critical advisory assessment — 2026-10-21

Source request: Discord thread/message 1562582544292249772, Rodolfo Mattei.
Scope: external research and read-only exposure assessment; no production update authorized/executed.

## Confirmed public facts

- PHP announced CVE-2026-109618 and CVE-2026-109619 on 2026-10-21; both rated CVSS 9.2. Under applicable conditions they allow unauthenticated remote code execution with web-worker privileges. PHP-FPM is in scope; exploitability is configuration/application dependent.
- Upstream fixed versions: 8.2.35, 8.3.36, 8.4.27, 8.5.12. Distributor backports must be judged by exact package revision, not just PHP_VERSION.
- Cloudflare reports observed attack traffic and automatic WAF protections; this does not establish exploitation or compromise of an MGS host. WAF mitigation does not replace patching.
- RunCloud announces automatic patching for supported PHP branches and temporary disabling of session.upload_progress. Latest extracted community update still described native builds in testing; live repository metadata subsequently showed patched packages available.
- Hostinger managed-hosting rollout is distinct from a self-managed VPS. The supplied email specifically asks VPS owners to verify their installations.

## Live findings

SSH audits succeeded on MatteiInc01 162.55.28.178, MatteiInc02 162.55.28.179 and MatteiInc03JBF 46.4.95.117. Each has active php83rc-fpm and binary /RunCloud/Packages/php83rc/sbin/php-fpm, PHP 8.3.33; installed native package 8.3.33-1+ubuntu22.04+1. No installed changelog hit for either CVE was found.

After successful apt-get update on each host, candidate is 8.3.36-1+ubuntu22.04+1. Dry-run scoped to installed PHP 8.3 core packages proposes exactly 21 upgrades on each host, no additions, removals or packages outside the frozen target lists. See rc-transactions.json for exact names.

FPM -i baseline has session.upload_progress.enabled=On. FPM -tt succeeds on each host; no explicit session.upload_progress.enabled pool override was emitted. A read-only scan of /etc/php83rc, /etc/php83rc-fpm and /etc/nginx-rc found no active explicit override. This does not substitute for a request-level proof of every running application's effective setting. Provider mitigation must not be credited as verified on these hosts.

Local Hostinger agent VPS: only PHP CLI packages installed, no PHP process observed. Installed php8.3-{cli,common,opcache,readline} is 8.3.6-0ubuntu0.24.04.12; after metadata refresh candidate is 8.3.6-0ubuntu0.24.04.13, the fixed revision named by Ubuntu USN-8948-1. Simulation proposes precisely these four upgrades and no additions/removals. HTTP PHP exposure was not observed; lower priority than the web hosts.

## Limitations and tool recovery

RunCloud API returned HTTP 429, rate remaining 0, and Retry-After approximately 1.8 million seconds. A bounded retry did not recover. Further API calls stopped; existing authorized SSH provided runtime evidence without credential changes. No current exhaustive portfolio/app enumeration was completed. Other RunCloud hosts, Hestia, AWS/Bitnami and embedded runtimes remain unverified by this assessment.

The paired web-backend benchmark could not start because the active Python environment lacks yaml. Normal web_search reported missing ddgs but returned successful Exa failover results. Primary-source extraction succeeded. The initially attempted php.net /security/2026-10-21 URL was 404; the source-linked /archive/2026.php#2026-10-21-5 recovered the official advisory. No runtime package installation, credential change, billing change or gateway restart was attempted to repair research tooling. No paired Perplexity/free comparison was completed.

No exploit, intrusive scanner, compromise investigation, production package installation, PHP restart, application configuration change or site-content mutation was performed. Metadata refreshes, reports/checkpoint/inventory/audit bookkeeping and a reusable skill reference are the only writes.

## Recommendation and decision gate

Urgently apply the vendor PHP 8.3 patch in place on the three confirmed web hosts, with scoped backup/rollback, exact transaction revalidation, PHP-FPM worker replacement and application canaries. Do not migrate to 8.4/8.5 or update plugins/themes unnecessarily. Local CLI patch is a separate four-package host scope. All installation/service changes await explicit Critical Subset confirmation. Pending approval is not remediation completion.

## Primary sources

- https://www.php.net/archive/2026.php#2026-10-21-5
- https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w
- https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp
- https://thephp.foundation/blog/2026/10/21/todays-php-security-release-and-how-were-strengthening-php-security/
- https://community.runcloud.io/t/critical-php-vulnerabilities-cve-2026-109618-cve-2026-109619-what-runcloud-is-doing/4814
- https://blog.cloudflare.com/php-vulnerabilities-waf-protection/
- https://ubuntu.com/security/notices/USN-8948-1
- https://statuspage.hostinger.com/
