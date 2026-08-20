## SEÇÃO B — Deploy de mu-plugins nos 4 sites AWS/Bitnami

Para deploy de arquivos PHP em `wp-content/mu-plugins/` nos 4 sites fora do RunCloud (openzed.com, finanzas.openzed.com, cliquet.com, finanzas.cliquet.com), ver o guia completo em:

**`references/bitnami-mu-plugin-deploy.md`** — fluxo elFinder, WPCode snippet, validação REST API, exit checklist, política de canário, pitfalls críticos de backslash/b64.

### Resumo dos métodos disponíveis

| Método | Risco | Quando usar |
|---|---|---|
| **elFinder `cmd: put`** | ✅ Baixo | Sempre preferido. Escreve em disco, não executa PHP. |
| **SFTP (`wpfiles`)** | ❌ Read-only | `wpfiles` é 100% read-only — não consegue escrever. |
| **WPCode snippet** | ❌ Alto | Última opção. Parse error = site DOWN irrecuperável sem .pem. |
| **SSH bitnami + .pem** | ✅ Melhor | Quando .pem disponível — acesso direto. |

Credenciais WP Admin (browser login): itens canônicos `Wordpress - SITE`, campos `username` + `password`.
Credenciais REST API: `api_auth_user` + `api_application_password`; exceção `cliquet.com`, que usa `username` + `wp_app_password`. Se houver título duplicado, selecionar o UUID por campos esperados e validar `/wp-json/wp/v2/users/me?context=edit` (HTTP 200, administrator) antes de qualquer write.

---

## SEÇÃO C — RunCloud API v3 e Setup SSH

Para configuração completa da RunCloud API v3 (autenticação, paginação, inventário de webapps) e setup de SSH com chave/usuário zeus para deploy direto nos servidores RunCloud, ver:

**`references/runcloud-api-ssh-setup.md`** — endpoints API, IDs de servidores, SSH key vault, Fail2Ban, firewall, sshpass, deploy em massa validado.

**`references/custom-wp-plugin-cutover.md`** — padrão MGS para migrar fluxo SaaS/builder/static app para plugin WordPress próprio em um site, com backup, lint remoto, WP-CLI install, import de configs, remoção segura de pastas estáticas que sombreiam rewrites, validação SMS/UTM e rollback.

**`references/openzed-chat-funnels-canary.md`** — deploy canário validado do plugin `MGS Chat Funnels` em OpenZed: upload/replace via WP Admin, ativação via REST plugins endpoint, validação de rotas `/chat/emp/br1` e `/chat/car/br1`, UTM passthrough e pitfall de JSON em `<script type="application/json">` sem `esc_html`.

**`references/chat-funnels-ad-wrapper-contract.md`** — contrato correto para anúncios nos MGS Chat Funnels: preservar `gpt.js`, wrapper JBF, `window.tags`, chamada única de `requestRewardAds()`, `showRewardedAds()` no CTA e `.ad-unit.ad`/`onInfinitePostLoaded`; não criar campos de auctions/timeout nem lógica própria de ads no plugin.

**`references/wp-plugin-json-config-render-validation.md`** — checklist para plugins com rotas públicas + admin UI: validar frontend live com DOM/JSON.parse/gate renderizado e validar admin apenas com sessão autenticada; `curl` deslogado em `/wp-admin` não prova a admin page., chamada única de `requestRewardAds()`, `showRewardedAds()` no CTA e `.ad-unit.ad`/`onInfinitePostLoaded`; não criar campos de auctions/timeout nem lógica própria de ads no plugin.

**`references/wp-plugin-json-config-render-validation.md`** — checklist para plugins com rotas públicas + admin UI: validar frontend live com DOM/JSON.parse/gate renderizado e validar admin apenas com sessão autenticada; `curl` deslogado em `/wp-admin` não prova a admin page.

**`references/wp-custom-plugin-public-routes-global-hooks.md`** — regra operacional para plugins MGS com rotas públicas (`/chat/...`, quiz etc.): URLs devem se comportar como páginas/posts normais do WordPress, herdando `wp_head()`, `wp_body_open()` e `wp_footer()` para WPCode/GTM/Yoast/pixels/scripts globais; canário OpenZed validado antes de rollout amplo.

**`references/wp-frontend-cache-vs-origin-validation.md`** — diagnóstico quando rota WP retorna 200 mas frontend público segue vazio/antigo após fix: comparar bare URL vs cachebuster, headers Cloudflare/APO (`cf-cache-status`, `age`, `cf-apo-via`), asset `ver=`, JSON cru no script e browser render; se cachebuster funciona e bare URL falha, tratar como purge de cache, não regressão do plugin.

**`references/wp-quiz-frontend-sms-diagnostic.md`** — diagnóstico quando leads aceitas pela API do SMS Funnel não aparecem na dashboard: diferenciar teste direto, endpoint WP e preenchimento real no frontend; validar `sms_funnel_status`, `success:true` e `list_id`; e renderizar split redirect com botão `+ Adicionar URL` em vez de JSON para operadores.r; se cachebuster funciona e bare URL falha, tratar como purge de cache, não regressão do plugin.

**`references/wp-quiz-frontend-sms-diagnostic.md`** — diagnóstico quando leads aceitas pela API do SMS Funnel não aparecem na dashboard: diferenciar teste direto, endpoint WP e preenchimento real no frontend; validar `sms_funnel_status`, `success:true` e `list_id`; e renderizar split redirect com botão `+ Adicionar URL` em vez de JSON para operadores.

Para manutenção segura do inventário RunCloud, ver também **`references/runcloud-inventory-hardening.md`**: paginação `meta.pagination.total_pages`, `--dry-run`/`--json`, token via 1Password sem exposição, tempfiles fora do repo, retry/backoff para 403/429/5xx e checklist de validação.

### Referência rápida

- **Base URL**: `https://manage.runcloud.io/api/v3`
- **Auth**: `Bearer TOKEN` (via `op item get "RunCloud API - MGS" --vault "MGS Conteúdo" --fields label=runcloud_api_key_token --reveal`)
- **Paginação**: `?perPage=40&page=N` (máx 40). Preferir `meta.pagination.total_pages`; usar `meta.lastPage` só como fallback legado. A API v3 já retornou `total_pages` e ignorou tentativas de aumentar `perPage` acima do padrão em alguns endpoints.
- **API v3 NÃO suporta escrita de arquivos** — deploy usa SSH/sshpass
- **Usuário deploy**: `zeus` (com sudo) nos 3 servidores RunCloud, credenciais no 1Password `"Runcloud Server 0X - IP- zeus Acesso"`

---

