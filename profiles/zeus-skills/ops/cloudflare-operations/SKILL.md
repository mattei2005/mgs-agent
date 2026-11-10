---
name: cloudflare-operations
description: "Use when Rodolfo asks Zeus to operate Cloudflare for MGS domains: purge cache, inspect zones/DNS/settings, or prepare DNS/SSL/WAF/rules changes. Covers 1Password token handling, zone resolution including subdomains, confirmation rules, API calls, audit logging, and reporting."
version: 1.1.3
author: Zeus MGS
license: Proprietary
metadata:
  hermes:
    tags: [mgs, cloudflare, cache, dns, infra, audit]
    related_skills: [discord-ops, log-monitor-discord-alert]
---

# Cloudflare Operations — MGS

## Overview

Zeus can operate Cloudflare for MGS using an API token stored in 1Password. The normal high-frequency action is cache purge. Broader Cloudflare changes such as DNS, SSL/TLS, WAF, Page Rules, Rulesets, Workers routes, or Zone Settings are allowed only when Rodolfo asks for the specific action, and require an explicit pre-apply confirmation with the exact change.

Never expose Cloudflare tokens or 1Password secret values in Discord, logs, reports, code blocks, or error excerpts. Only report item names, field names, token verification status, zone names, HTTP status, and Cloudflare result IDs/prefixes.

## When to Use

Use this skill when Rodolfo asks to:

- clear/limpar/purge Cloudflare cache for one or more MGS domains;
- test or validate Zeus Cloudflare access;
- list or resolve Cloudflare zones for MGS domains;
- inspect DNS/settings/rules before a change;
- prepare or apply specific Cloudflare changes after approval.

Do not use this skill for WordPress application cache, RunCloud cache, plugin cache, browser cache, or CDN providers other than Cloudflare unless Rodolfo explicitly says Cloudflare is involved.

## Explicar e escolher Full versus Full (strict)

- Quando Rodolfo perguntar a diferença, explique primeiro os dois trechos `visitante → Cloudflare → origem`. Para acessos HTTPS, ambos os modos criptografam os dois trechos; a diferença é a validação do certificado **da origem**, não o certificado público apresentado ao navegador.
- Explique que **Full** aceita o certificado da origem sem validar confiança, validade ou correspondência do hostname; **Full (strict)** exige certificado não vencido, correspondente ao domínio e emitido por CA pública confiável ou Cloudflare Origin CA. O cadeado público pode continuar normal em Full mesmo quando o certificado da origem está incorreto.
- Traduza o efeito operacional: strict não é WAF, CAPTCHA nem restrição de visitantes/bots. Com certificado válido, não altera por si só CTAs ou UTMs. Se a validação do certificado falhar, pode ocorrer526; não prometa disponibilidade apenas porque a opção está selecionada.
- Trate a informação de que Rodolfo costuma usar Full como contexto, não como ordem para trocar o site atual ou migrar o portfólio. Em perguntas explicativas, responda sem executar mudanças e sem abrir uma auditoria de todos os sites. Para implantação nova, proponha o modo e seu requisito de certificado no diff autorizado; para sites existentes, preserve a configuração até haver instrução específica.
- Para recomendar strict num alvo concreto, confira separadamente certificado de origem, cadeia/hostname/validade e HTTPS público. Consulte as referências oficiais: `https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full/` e `https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/`.
- Diante de521/522 junto com timeout SSH, investigue conectividade e eventual reinício antes de culpar strict ou reduzir a validação TLS. Após recuperação, repita o conjunto exato de URLs afetadas; boot recente comprova reinício, não seu autor ou causa.

## Block/challenge investigation: establish the traffic path first

1. Before credential discovery, resolve the exact hostname's A, AAAA and CNAME records and the apex NS. Use DNS-over-HTTPS, for example `GET https://dns.google/resolve?name=<hostname>&type=A`, and confirm an unexpected answer through `https://cloudflare-dns.com/dns-query` with `Accept: application/dns-json`. Preserve the distinction between authoritative DNS and HTTP proxying: external nameservers alone do not exclude a Cloudflare partial/CNAME setup.
2. Fetch the homepage and a representative affected article with redirects enabled. Record final URL, HTTP status, `Server`, `CF-Ray`, `CF-Mitigated`, `CF-Cache-Status` and challenge-page markers. Combine the address/CNAME chain with HTTP evidence; neither a missing header nor a 404 at `/cdn-cgi/trace` independently proves Cloudflare absence.
3. If the current path resolves directly to the known origin and responses identify another WAF, report that topology and the observation's limits before requesting Cloudflare access. An empty token-scoped zone lookup is supporting access evidence, not proof that no Cloudflare account owns the domain. Do not rotate credentials or broaden token permissions to diagnose a WAF that is not on the observed path.
4. Distinguish page protection from external ad delivery: an origin page returning 200 does not establish that third-party scripts or creatives succeeded. A successful local probe also does not exclude country/IP/device-specific or historical blocking.
5. When asked what access is needed next, first check existing authorized SSH/login references and perform a bounded read-only log-directory probe using the server-access skill. Separate authentication, directory readability, retained incident records and cloud-console access; a readable directory is not a completed incident analysis. Request only the missing time window/timezone or exact unavailable capability, never credentials in chat. Discovery of another WAF is not authorization to change its protection.

## Scoped access-discovery handoffs

When the operator asks only to certify an existing credential route, keep the handoff read-only and preserve that operator as executor. Verify approved tokens and query only the exact target zone; never issue a test purge, repeat origin invalidation, create/rotate a token, elevate a role, or enumerate all Cloudflare zones. Reduce 1Password metadata to the approved Cloudflare identities and literal target-specific candidates before printing or persisting; do not expose unrelated domain/app credential catalogs merely because their titles match Cloudflare. An active token plus HTTP-200/zero exact-zone results proves no visible target binding through that token at that observation, not an invalid token, absence of the zone everywhere, the owning account, or purge permission. If Rodolfo identifies the existing account or disputes an empty lookup, re-read the exact 1Password item and repeat the exact-zone GET before asking for new access. When the zone becomes visible, independently GET its returned zone ID, inspect the returned `#cache_purge:edit` permission without issuing a test purge, and persist a superseding access receipt for the current operator. Do not invent a cause for a prior zero-result response that cannot be reproduced. Public nameservers confirm DNS delegation, not account ownership. If no route is certified, return the single missing existing identity/zone/credential capability and its internal owner; do not reopen editorial approval or touch targets already completed by the operator.

## Routine Cache Purge Fast Path

For a direct cache-purge request from Rodolfo, loading this skill completes the procedural lookup. Execute from this documented procedure immediately; do **not** search the repository for Cloudflare scripts, reopen `AGENT.md`, or run broad confirmation-rule searches when the request and zone scope are already clear.

Limit prerequisite work to the required live checks: validate the token, resolve the requested hostname to its Cloudflare zone, purge, append the audit event, and validate the audit readback. Search other files only when this skill is missing or broken, the hostname-to-parent-zone scope is ambiguous, the API path fails, or Rodolfo explicitly asks for an audit/investigation. This keeps routine purges fast and avoids unnecessary visible `Searching...` churn in Discord.

## Credential Source

Canonical 1Password item currently used by Zeus:

- Vault: `MGS Conteúdo` via `OP_DEFAULT_VAULT`
- Item: `Cloudflare MGS Admin Token - mattei2005`
- Preferred field: `token`

An alternate item, `Cloudflare MGS Admin Token - mattei20052`, may validate as active but has a different zone scope. Never select a token only because `/user/tokens/verify` succeeds: query the exact target zone and use the item that returns it. Live read-only validation confirmed that token scope is split by zone: `pdllifestyle.com` is visible through `mattei2005` and not through `mattei20052`; `zuout.com` is visible through `mattei20052` and not through `mattei2005`. Always resolve the exact zone against each approved token scope before choosing the credential.

Load credentials with `.env` exported for subprocesses:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
```

Then resolve the item through `op`. Do not print the token. If multiple token-like fields exist, prefer the exact field label `token`; validate with `/user/tokens/verify` before using it.

## Authorization and Confirmation Rules

Resolve the current `data/authorized-users.json` before interpreting the CEO-only defaults below. In infra-dev (`1566814313086193795`) and its child threads, Rodolfo's decision `1567593717487902802` delegates to `santosoliv_dev_br` (`963808102891798649`) equivalent site/endpoint-scoped Cloudflare WAF protections, such as the Wavesbee Managed Challenge pilot. His explicit request and scoped confirmation suffice without a new CEO confirmation. Preserve legitimate/public access, a single executor, exact diff, backup/rollback and API/public verification. This exception does not authorize server firewall/Fail2Ban/SSH, credentials/permissions, billing, account-global or indiscriminate portfolio changes, or other Critical Subset operations. The canonical delegation wins over historical blanket escalations in this skill.

For a login challenge pilot, compare an automated request before/after (`cf-mitigated: challenge` proves edge interception) and recheck public pages, the existing custom login, XML-RPC and excluded hosts. A browser challenge is not an allow guarantee for all humans, and passing it does not restore an application route that already returned 404. Say so rather than promising a working default login. Reuse only the explicitly approved disabled rule when the Free-plan rule quota is full; PATCH that single rule and compare every unrelated rule and Bot Management setting by semantic readback. Preserve the rollback snapshot outside ephemeral scratch.

1. **Read-only checks** — token verify, zone list, DNS list, settings read — may run immediately when Rodolfo asks to test/inspect.
2. **Cache purge** — destructive but low-risk. If Rodolfo says “confirma antes”, do a read-only precheck and wait for explicit confirmation. If Rodolfo directly asks to purge and does not ask for confirmation, purge may proceed, but for multi-site purge prefer one concise precheck confirmation.
3. **DNS/SSL/WAF/rules/settings changes** — always show the exact intended diff/action and ask for explicit confirmation before applying.
4. **Account-wide or cross-zone changes** — confirm scope clearly, especially when a requested hostname is a subdomain whose Cloudflare zone is the parent domain.
5. **Billing, ownership, account members, token creation/deletion, or global security settings** — treat as sensitive; require explicit instruction and confirmation.

### Creating Additional API Tokens

Cloudflare's current official flow requires the initial token to be generated from the dashboard template **Create additional tokens**. The `User → API Tokens → Edit` permission (API name: `API Tokens Write`) is not available in other templates or in the Custom Token builder.

For a safe capability smoke test after Rodolfo's Critical Subset confirmation:

1. Verify the initial token is active.
2. Resolve its exact `com.cloudflare.api.user.<USER_TAG>` resource from the current token policy; do not expose the user tag or token IDs in Discord.
3. Create a short-lived temporary token with the smallest useful permission (for example, `User Details Read`) and a near-term expiration as a cleanup fallback.
4. Verify the temporary token through `/user/tokens/verify`.
5. Delete it immediately with the initial token.
6. Validate deletion by readback (`GET /user/tokens/{id}` returning not found) and append a secret-free audit event.

`API Tokens Read` alone does not authorize `POST /user/tokens`; creation requires `API Tokens Write`.

A token created through the API is a sub-token and cannot itself receive permission to manage other tokens. Cloudflare rejects that recovery-token pattern with error `1001: sub-token is not allowed to have permissions to manage other tokens`. Do not rely on an API-created token as rollback authority for editing the only token-management credential. Require either an independently dashboard-created management credential or a new Critical Subset confirmation for an atomic self-update with manual dashboard rollback if access is lost.

## Zone Resolution

Cloudflare zones are usually apex domains. For a requested hostname:

1. Try exact zone name first, e.g. `openzed.com`.
2. If not found and the request is a subdomain, progressively try parent zones, e.g. `finance.topfeed.fun` → `topfeed.fun`.
3. Report the mapping before purge when confirmation is requested.
4. If a subdomain maps to parent zone, state that purge applies to the whole parent zone when using `purge_everything`.

Known observed mappings from validated purges:

```text
finance.topfeed.fun  -> topfeed.fun
finanzas.topfeed.fun -> topfeed.fun
```

For either subdomain, `purge_everything` clears the complete `topfeed.fun` zone, including cache for sibling hostnames. State that actual scope explicitly in the final report even when the user asked only for one subdomain.

## Cache Purge Procedure

Use Cloudflare endpoint:

```text
POST /client/v4/zones/{zone_id}/purge_cache
Body: {"purge_everything": true}
```

Operational steps:

1. Verify token:
   - `GET /user/tokens/verify`
   - Completion: HTTP 200, `success=true`, token status `active`.
2. Resolve each requested site to a Cloudflare zone:
   - `GET /zones?name=<candidate>&per_page=5`
   - Completion: every requested site has a zone or is explicitly reported missing.
3. If confirmation was requested, stop and show a short mapping table:
   - requested hostname;
   - matched Cloudflare zone;
   - zone status;
   - warning for parent-zone purge.
4. After confirmation, call purge endpoint once per zone.
   - Completion: every call returns HTTP 200 and `success=true`.
5. Append audit event to `/root/mgs-agent/logs/events-audit.jsonl`.
   - Include timestamp, actor, agent, mode, requested sites, zones, HTTP statuses, success flags, Cloudflare result IDs/prefixes, and token item name.
   - Exclude secrets and full token values.
6. Report concise final status in Discord.

## Purge seletivo por arquivo e cache keys com query

Para purgar somente arquivos autorizados, use o mesmo endpoint com:

```text
POST /client/v4/zones/{zone_id}/purge_cache
Body: {"files":["https://example.com/path/file.css?ver=123", "..."]}
```

- Trate a query string como parte da cache key. Purgar `file.css` não prova que `file.css?ver=123` saiu do edge.
- Derive as URLs exatas do HTML público que o navegador realmente carrega; não adivinhe `?ver=` nem amplie para `purge_everything`.
- Quando bare path e variante com query existirem, purge a variante efetivamente usada. Um retry sobre a mesma folha com a query correta continua sendo purge seletivo do mesmo arquivo, mas registre ambas as chamadas.
- Após o purge, valide cada URL exata: HTTP `200`, `CF-Cache-Status` compatível com revalidação (`MISS`/`DYNAMIC` no primeiro fetch), conteúdo sem o valor antigo e hash igual ao da origem. Depois execute o canário em navegador, porque `curl` no bare path pode passar enquanto o browser continua recebendo uma variante query-string antiga.

## Minimal Python Pattern

Use this as the base pattern when no wrapper script exists yet. Keep output small.

```python
import json, os, subprocess, urllib.parse, urllib.request, urllib.error

ITEM = 'Cloudflare MGS Admin Token - mattei2005'
VAULT = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')
obj = json.loads(subprocess.check_output(['op','item','get',ITEM,'--vault',VAULT,'--format','json'], text=True))
token = next(f['value'] for f in obj['fields'] if (f.get('label') or '').lower() == 'token')

def cf(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        'https://api.cloudflare.com/client/v4' + path,
        data=data,
        method=method,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {'success': False, 'errors': [{'message': body[:300]}]}
        return e.code, parsed
```

## Reporting Format

For final purge reports, use compact aligned rows:

```text
Site                 Zona Cloudflare      HTTP  Status
-------------------  -------------------  ----  ------
eggbev.com           eggbev.com           200   OK
finance.topfeed.fun  topfeed.fun          200   OK
```

Mention whether audit logging happened. Do not include raw JSON unless Rodolfo asks.

## Histórico de timeout e Analytics

- Para investigar um incidente, resolva a zona exata e consulte Analytics para o intervalo UTC com margem antes/depois, distinguindo status de edge/origem e eventos de segurança da sonda quando o dataset/plano permitir. Sucesso atual e logs de origem isolados não comprovam ausência de falha entre sonda e edge.
- Valide `errors` e `data` no JSON GraphQL: HTTP 200 com `data:null` e `extensions.code=authz` é consulta bloqueada, nunca zero erros/requests. A permissão faltante observável `com.cloudflare.api.account.zone.analytics.read` corresponde à leitura de Zone Analytics; token ativo e DNS/cache editáveis não a comprovam.
- Confirme limites/datasets pela descoberta de settings da zona e pela documentação oficial atual, não por suposição sobre Free/Pro. Ausência de acesso é lacuna de observabilidade, não ausência de incidente. Preserve amostragem e resolução no relato.
- Após PUT de token, compare as políticas por multiconjunto semântico (effect, resources e IDs dos permission_groups), preservando também nome/status/restrições. A Cloudflare pode reordenar as políticas no GET; divergência só de ordem exige corrigir o verificador e reler o alvo, nunca reaplicar a mudança.
- Use discovery de settings antes de selecionar o dataset: `httpRequests1mGroups` pode estar desabilitado enquanto `httpRequestsAdaptiveGroups` está disponível. Preserve `avg.sampleInterval` e não apresente contagens adaptativas como logs completos. Valide campos opcionais pela introspecção do schema: `availableFields` sozinho não garante que um nome como `rayName` seja aceito no objeto GraphQL consultado.
- Para separar aplicação de transporte em 522/525/524 intermitentes, cruze dados Cloudflare com o estado TCP do kernel, recursos e uma captura passiva curta na NIC externa. Vincule os fluxos ao domínio pelo SNI do ClientHello; reduza a captura em memória a metadados e não persista payload, cookies ou segredos. SYN+ACK imediato seguido por SYNs repetidos e retransmissões reconhecidas por `ss -ti` comprova degradação de transporte, mas não identifica sozinho o provedor/equipamento culpado.
- Não interprete saltos MTR sem resposta ou perda em roteador intermediário como perda fim a fim quando o destino não respondeu. Registre o trace como inconclusivo nesse ponto e fundamente a degradação em tráfego TCP real; redução de MSS por PMTU probing é indício complementar, não autorização para alterar MTU/sysctl globalmente.
- Não declare falta de whitelist Cloudflare sem comparar a cobertura com `GET /client/v4/ips` e os sets/regras vivos. Diferencie a origem de rede Cloudflare do IP real da sonda reconstruído por proxies. Recursos folgados durante falhas atuais ajudam a excluir saturação contemporânea, mas não reconstituem CPU/memória de um intervalo histórico sem coletor.
- Não altere permissões de token para recuperar uma consulta sem a confirmação crítica específica. Preserve as políticas existentes e a autoridade independente de rollback; bloquearam API e painel, entregue o diagnóstico exato e a única decisão necessária, sem loops ou envio de credenciais a proxies/arquivos públicos.

## Common Pitfalls

- For an origin restricted to Cloudflare source IPs, retrieve and validate the official list from `GET https://api.cloudflare.com/client/v4/ips` (`ipv4_cidrs` + `ipv6_cidrs`). The website `/ips-v4` or `/ips-v6` may return 403 on VPS requests; fail over to the official API rather than inventing CIDRs or weakening origin restrictions. Trust `CF-Connecting-IP` only after validating the actual peer against those networks.

1. **Token verifies but purge fails.** Token status `active` only proves token validity. Purge can still fail if `Zone → Cache Purge → Edit` is missing for the target zones. Fix Cloudflare token permissions and retry.
2. **Subdomain purge scope confusion.** `finance.topfeed.fun` maps to zone `topfeed.fun`; `purge_everything` clears the parent zone cache, not only that subdomain.
3. **Leaking secrets through debug output.** Avoid printing 1Password item JSON, field values, headers, env vars, or request objects.
4. **Assuming result ID is separate from zone ID.** Cloudflare purge responses may echo an ID that resembles the zone ID. Treat it as an API result handle; do not overinterpret.
5. **Skipping audit log.** Every write operation must append to `events-audit.jsonl` before reporting completion.

## Verification Checklist

- [ ] Correct 1Password item and field used without printing secrets.
- [ ] Token verify returned `success=true` and status `active`.
- [ ] Requested hostnames resolved to expected Cloudflare zones.
- [ ] Confirmation obtained when required.
- [ ] Every write call returned HTTP 2xx and `success=true`.
- [ ] Audit event appended with no secrets.
- [ ] Discord report is concise and includes any partial failures.
