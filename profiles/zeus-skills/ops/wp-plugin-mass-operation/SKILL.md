---
name: wp-plugin-mass-operation
description: "Operações WordPress em massa nos 31 sites MGS: WP-CLI (RunCloud SSH), browser automation (AWS/Bitnami), SFTP, elFinder/WPCode deploy de mu-plugins, e RunCloud API v3. Cobre infra completa (27 RunCloud + 4 Bitnami + fincgriffin), credenciais, 1Password, SSH setup e pitfalls críticos de deploy."
tags: [wordpress, wp-cli, plugin, mass-operation, runcloud, sftp, mu-plugins, bitnami, api, deploy, infra]
related_skills: [mgs-infra-inventory, log-monitor-discord-alert, shell-cron-env-export]
---

# Operações de Plugin WordPress em Massa — Sites MGS

## Quando usar
- Preciso instalar, ativar, desativar ou deletar um plugin em todos os 31 sites
- Preciso portar/migrar um fluxo de SaaS/builder/static app para plugin WordPress próprio em um site MGS (ex: quiz/lead capture com REST, rewrite, CSV, SMS Funnel)
- Preciso rodar um comando WP-CLI de plugin (ex: imagify bulk-optimize, yoast reindex) em massa
- Preciso verificar se um plugin está instalado/ativo em todos os sites
- Preciso revisar, preparar ou fazer cutover de plugin WordPress customizado que substitui stack externa (Lovable/Supabase/iframe/static app) em produção — ver `references/wordpress-quiz-plugin-migration.md` para o padrão validado de quiz/funil com SMS Funnel, leads e relatório
- Rodolfo pergunta se Zeus/Atena instalou um plugin ou se ele já estava presente — fazer auditoria de proveniência, não responder por memória
- Recebeu REPORT-INFRA de um agente e precisa atualizar o inventário de infra
- Auditoria da operação MGS (o que existe, onde, quem criou)
- Onboarding de novo agente — verificar o que já existe
- Migrar/cortar apps externos ou estáticos para plugin WordPress próprio com rotas públicas, captura de leads, integrações externas e dashboard/reporting — ver `references/custom-wp-plugin-cutover.md`

### Referência rápida — custom plugin cutover

Quando substituir Lovable/Supabase/static folders/iframes por plugin WP first-party, seguir `references/custom-wp-plugin-cutover.md`: validar REST admin, lint remoto, backup, desativar pastas físicas que sombreiam rewrites, salvar lead no WP + encaminhar server-side, importar histórico sem reenviar para vendor, e validar cada rota/lista com status armazenado.

Para UI operacional de quiz e diagnóstico SMS Funnel, ver `references/quiz-redirect-sms-diagnostics.md`: redirect split deve ser editável por linhas com `+ Adicionar URL`, URL + peso + remover; `redirect_variants` não deve ficar como JSON para operador; quando SMS Funnel dashboard mostrar zero mas WP recebeu `success:true` com `list_id` correto, tratar como provável delay/cache/indexação/deduplicação da plataforma SMS Funnel após validar com leads frescas por gestor.

### Referência rápida — revisão de plugin customizado de quiz

Quando revisar plugin customizado de quiz/lead capture gerado por Lovable/dev externo, usar o checklist em `references/wp-quiz-plugin-migration-review.md`: shortcode completo, segredo de SMS Funnel fora do público, sem redirect antes de `ok:true`, Pixel Lead só pós-sucesso, `require_sms_success` para cutover, anti-spam com timestamp obrigatório e canário antes de tráfego cheio.

### Referência rápida — proveniência WP File Manager

Quando a pergunta for "foi você que instalou o File Manager?", não pivotar para o último REC/P1 nem explicar publicação. Auditar evidências e responder a pergunta de accountability diretamente. Ver `references/wp-file-manager-provenance-audit.md`.

### Referência rápida — auditoria WP File Manager + mu-plugins

Quando Rodolfo trouxer preocupação de segurança sobre `mu-plugins`, WP File Manager, elFinder ou WPCode: não remover primeiro. Rodar auditoria read-only, separar achado acionável de diferença de arquitetura, e só depois pedir confirmação para desativar/deletar resíduos. Ver `references/wp-file-manager-mu-plugin-security-audit.md`.

---

## SEÇÃO PRÉ-FLIGHT — Inventário de Infraestrutura MGS

### Arquivo canônico e regeneração

```
/root/mgs-agent/data/infra-inventory.json
```

Gerado por: `/root/mgs-agent/scripts/infra-discovery.sh`

```bash
/root/mgs-agent/scripts/infra-discovery.sh
# Saída esperada (atualizado 2026-04-27):
# Serviços: 3 | Crons: 8 | Scripts: 16
# skills_mgs: 2 | skills_hermes: "atena=78, zeus=87"
```

O auto-commit watcher detecta a mudança e faz push automaticamente.

### Schema do JSON (chaves principais)

```json
{
  "_meta": { "updated_at": "...", "generated_by": "infra-discovery.sh" },
  "systemd_services": [ {"name": "...", "status": "active/running"} ],
  "crons": [ {"entry": "*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh ..."} ],
  "scripts": [ {"path": "...", "size_bytes": N, "modified_at": "..."} ],
  "skills_mgs": [
    {"name": "content-generate-rec", "path": "/root/mgs-agent/skills/.../", "skill_md": "..."}
  ],
  "skills_hermes": {
    "atena": [ {"name": "apple-notes", "category": "apple", "skill_md": "..."} ],
    "zeus":  [ {"name": "runcloud-api-management", "category": "ops", "skill_md": "..."} ]
  },
  "data_files": [ {"path": "...", "size_bytes": N, "md5": "...", "modified_at": "..."} ],
  "mu_plugin_canonical": {"path": "...", "md5": "...", "lines": N}
}
```

**⚠️ Pitfall:** chave canônica é `"crons"` (não `"cron_jobs"`). Validar:
```bash
jq '.crons | length' /root/mgs-agent/data/infra-inventory.json
# Deve retornar >= 1, não 0
```

### Separação skills_mgs vs skills_hermes

| Chave | Path | Propósito | Dispara REPORT-INFRA? |
|---|---|---|---|
| `skills_mgs` | `/root/mgs-agent/skills/` | Skills do **projeto MGS** | ✅ Sim |
| `skills_hermes` | `/root/.hermes/profiles/{agent}/skills/` | Capabilities internas do **framework Hermes** | ❌ Não |

**Números de referência (2026-04-27):** `skills_mgs`: 2 · `skills_hermes.atena`: 78 · `skills_hermes.zeus`: 87

### Processo após receber REPORT-INFRA

1. Validar mentalmente se o artefato reportado faz sentido
2. Se OK → rodar `infra-discovery.sh` para capturar o estado atual
3. Se identificar problema → escalar para Rodolfo
4. Silêncio ou ack curto no canal

### Validação real do inventário antes de mass operation (L2)

**Sempre validar o inventário real antes de executar em massa.**

Exemplo do acerto do Zeus em 2026-04-24:
- Briefing dizia "34 sites RunCloud"
- Cruzamento inventário (`inventario-webapps.json`) × `sites.md` = 26 sites reais
- Diferença: eggbev (canário já feito), fincgriffin (manual), 4 SFTP fora do RunCloud
- Zeus parou, reportou discrepância, aguardou confirmação → 0 sites tocados incorretamente

**Comando de cruzamento:**
```python
import json

with open('/root/mgs-agent/inventario-webapps.json') as f:
    inventory = json.load(f)

mgs_sites = { ... }  # domínios de sites.md
excluded = {'eggbev.com', 'fincgriffin.com'}
sftp_sites = {'openzed.com', 'finanzas.openzed.com', 'cliquet.com', 'finanzas.cliquet.com'}

target = [s for s in inventory
          if s.get('primary_domain') in mgs_sites
          and s.get('primary_domain') not in excluded
          and s.get('primary_domain') not in sftp_sites]

print(f"Total real para deploy: {len(target)}")
```

**Nota:** Para contagem de sites/webapps MGS, ver `docs/site-counting.md`. **32 sites MGS oficiais** (fonte: `context/sites.md`), 27 em RunCloud, 5 em SFTP. Os 107 webapps RunCloud incluem não-MGS — não são fonte de verdade pra contagem MGS.

### Atualizar inventário manualmente (sem rodar script)

```bash
jq '.mu_plugin_canonical.deploy_status.eggbev_com = "deployed_v2"' \
  /root/mgs-agent/data/infra-inventory.json > /tmp/inv.json \
  && mv /tmp/inv.json /root/mgs-agent/data/infra-inventory.json
```

O auto-commit watcher vai detectar e fazer push.

---

## Infraestrutura dos 31 sites MGS

### RunCloud (27 sites) — WP-CLI via SSH
| Servidor | IP | User sudo | Sites |
|---|---|---|---|
| MatteiInc01 | 162.55.28.178 | zeus | 17 sites |
| MatteiInc02 | 162.55.28.179 | zeus | 2 sites |
| MatteiInc03JBF | 46.4.95.117 | zeus | 8 sites |

Credenciais: `op item get "Runcloud Server 0X - IP- zeus Acesso" --vault "MGS Conteúdo" --fields label=password --reveal`

**CRÍTICO:** Buscar senha via `terminal()` do hermes_tools, NÃO via subprocess Python — o subprocess não tem acesso ao token de serviço do 1Password.

### AWS/Bitnami (4 sites) — Browser automation
- finanzas.openzed.com, openzed.com, finanzas.cliquet.com, cliquet.com
- Login em `SITE/rodloguda` com credenciais do 1Password
- WP-CLI não disponível (não há SSH com usuário runcloud)

### Sem acesso programático
- fincgriffin.com — fazer manualmente

---

## Mapeamento completo dos 27 sites RunCloud

```python
SITES_RUNCLOUD = {
    "162.55.28.178": {  # MatteiInc01
        "op_item": "Runcloud Server 01 - 162.55.28.178- zeus Acesso",
        "sites": [
            ("/home/runcloud/webapps/eggbev", "eggbev.com", "runcloud"),
            ("/home/runcloud/webapps/finance-wantabrand", "finance.wantabrand.com", "runcloud"),
            ("/home/runcloud/webapps/finanzas-eggbev", "finanzas.eggbev.com", "runcloud"),
            ("/home/runcloud/webapps/finanzas-lyzmo", "finanzas.lyzmo.com", "runcloud"),
            ("/home/runcloud/webapps/lyzmo", "lyzmo.com", "runcloud"),
            ("/home/runcloud/webapps/newsoun", "newsoun.com", "runcloud"),
            ("/home/runcloud/webapps/newsoun-de", "de.newsoun.com", "runcloud"),
            ("/home/runcloud/webapps/newsoun-finanzas", "finanzas.newsoun.com", "runcloud"),
            ("/home/runcloud/webapps/seuprimeiroempleo", "empleo.seuprimeiroempregoam.com", "runcloud"),
            ("/home/runcloud/webapps/seuprimeiroempregoam", "seuprimeiroempregoam.com", "runcloud"),
            ("/home/runcloud/webapps/topfeedfinance", "finance.topfeed.fun", "runcloud"),
            ("/home/runcloud/webapps/topfeedfinance-finanzas", "finanzas.topfeed.fun", "runcloud"),
            ("/home/runcloud2/webapps/wantabrand", "wantabrand.com", "runcloud2"),  # runcloud2!
            ("/home/runcloud/webapps/zuout", "zuout.com", "runcloud"),
            ("/home/runcloud/webapps/zuout-finanzas", "finanzas.zuout.com", "runcloud"),
            ("/home/runcloud/webapps/zytiva", "zytiva.com", "runcloud"),
            ("/home/runcloud/webapps/zytiva-finanzas", "finanzas.zytiva.com", "runcloud"),
        ]
    },
    "162.55.28.179": {  # MatteiInc02
        "op_item": "Runcloud Server 02 - 162.55.28.179- zeus Acesso",
        "sites": [
            ("/home/runcloud2/webapps/creditoparaveiculo", "creditoparaveiculo.com", "runcloud2"),  # runcloud2!
            ("/home/runcloud2/webapps/gamezonead", "gamezonead.com", "runcloud2"),  # runcloud2!
        ]
    },
    "46.4.95.117": {  # MatteiInc03JBF
        "op_item": "Runcloud Server 03 - 46.4.95.117- zeus Acesso",
        "sites": [
            ("/home/runcloud/webapps/ducapes", "ducapes.com", "runcloud"),
            ("/home/runcloud/webapps/ducapes-finance", "finance.ducapes.com", "runcloud"),
            ("/home/runcloud/webapps/FinanceADX", "financeadx.com", "runcloud"),
            ("/home/runcloud/webapps/helixenit", "helixenit.net", "runcloud"),
            ("/home/runcloud/webapps/infinitynexx", "infinitynexx.com", "runcloud"),
            ("/home/runcloud/webapps/marevelx", "marevelx.com", "runcloud"),
            ("/home/runcloud/webapps/vizioid", "vizioid.com", "runcloud"),
            ("/home/runcloud/webapps/xyvlov", "xyvlov.com", "runcloud"),
        ]
    }
}
```

---

## Padrão de execução em massa via WP-CLI

```python
from hermes_tools import terminal

def run_wpcli_all_servers(wp_command_template):
    """
    wp_command_template: string com {path} e {user} como placeholders
    Ex: "sudo -u {user} wp --path={path} plugin activate imagify --allow-root"
    """
    for ip, config in SITES_RUNCLOUD.items():
        # Pegar senha via terminal (não subprocess)
        r = terminal(f'op item get "{config["op_item"]}" --vault "MGS Conteúdo" --fields label=password --reveal 2>&1')
        password = r['output'].strip()

        # Montar script bash
        lines = "#!/bin/bash\n"
        for path, domain, user in config['sites']:
            cmd = wp_command_template.format(path=path, user=user)
            lines += f'echo "=== {domain} ==="\n{cmd} 2>&1 | tail -3\n'

        script_path = f'/tmp/wpcli_{ip.replace(".", "_")}.sh'
        with open(script_path, 'w') as f:
            f.write(lines)

        result = terminal(
            f'sshpass -p {repr(password)} ssh -o PreferredAuthentications=password '
            f'-o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new '
            f'-o UserKnownHostsFile=/root/.ssh/known_hosts_mgs '
            f'zeus@{ip} \'bash -s\' < {script_path}',
            timeout=600
        )
        print(f"\n=== SERVER {ip} ===")
        print(result['output'])
```

### Exemplos de uso

```python
# Instalar + ativar plugin
run_wpcli_all_servers("sudo -u {user} wp --path={path} plugin install imagify --activate --allow-root")

# Disparar bulk operation de plugin
run_wpcli_all_servers("sudo -u {user} wp --path={path} imagify bulk-optimize library --allow-root")

# Verificar se plugin está ativo
run_wpcli_all_servers("sudo -u {user} wp --path={path} plugin list --allow-root 2>&1 | grep -i imagify || echo 'NAO ENCONTRADO'")

# Desativar plugin
run_wpcli_all_servers("sudo -u {user} wp --path={path} plugin deactivate PLUGIN_SLUG --allow-root")
```

---

## Validação real pós-operação

Não confiar apenas no output do WP-CLI. Validar via banco de dados:

```python
# Exemplo: confirmar imagens Imagify otimizadas
run_wpcli_all_servers(
    "sudo -u {user} wp --path={path} db query "
    "\"SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='_imagify_data' AND meta_value LIKE '%optimized%';\" "
    "--allow-root 2>&1 | tail -1"
)
```

---

## Sites AWS/Bitnami — browser automation

Para estes 4 sites, o padrão é:
1. Login em `SITE/rodloguda` com credenciais do 1Password (item `SITE wordpress zeus`, campo `username` + `password`)
2. Navegar para a página do plugin
3. Interagir via `mcp_browser_console` com `document.getElementById('ID_DO_BOTAO').click()`

**Credenciais AWS sites:**
| Site | Item 1Password |
|---|---|
| finanzas.openzed.com | `openzed finanzas wordpress zeus` |
| openzed.com | `openzed wordpress zeus` |
| finanzas.cliquet.com | `cliquet finanzas wordpress zeus` |
| cliquet.com | `cliquet wordpress zeus` |

**⚠️ cliquet.com:** senha no WP pode ser `Zeus_Deploy_2024!` (não `Brasil31733@` que está no 1P) — foi alterada emergencialmente em 23/04/2026. Verificar qual funciona.

---

## ⚠️ Pitfalls

1. **`sudo -u runcloud` falha em sites do runcloud2** — wantabrand (Inc01), creditoparaveiculo e gamezonead (Inc02) estão em `/home/runcloud2/` e pertencem ao usuário `runcloud2`. Usar `sudo -u runcloud2`. Verificar com `ls -la /home/runcloud2/webapps/`.

2. **Plugin instalado mas inativo** — WP-CLI retorna `'X' is not a registered wp command` se plugin está instalado mas inativo. Sempre rodar `plugin install SLUG --activate` (o `--activate` é ignorado se já estiver ativo, mas ativa se estiver inativo).

3. **Subprocess Python não acessa 1Password** — `subprocess.run(['op', 'item', 'get', ...])` retorna vazio/erro porque o subprocess não herda o token de serviço do ambiente. Usar sempre `terminal('op item get ...')` do hermes_tools.

4. **Warning "Permission denied" em mu-plugins** — alguns sites (lyzmo.com) mostram warning de permissão ao rodar WP-CLI. Não bloqueia a operação — ignorar.

5. **`wp imagify info` não tem output útil** — usar query no banco `_imagify_data` para validação real.

6. **`apiDown: true` no browser Imagify** — a API do Imagify é externa. Se o servidor AWS/Bitnami não tiver saída para `api.imagify.io`, o bulk não dispara pelo browser. Verificar `window.imagifyBulk.apiDown` no console.

---

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

Credenciais WP Admin (browser login): `op item get "SITE wordpress zeus" --vault "MGS Conteúdo" --fields label=username`
Credenciais REST API: campos `api_auth_user` + `api_application_password` no mesmo item.

---

## SEÇÃO C — RunCloud API v3 e Setup SSH

Para configuração completa da RunCloud API v3 (autenticação, paginação, inventário de webapps) e setup de SSH com chave/usuário zeus para deploy direto nos servidores RunCloud, ver:

**`references/runcloud-api-ssh-setup.md`** — endpoints API, IDs de servidores, SSH key vault, Fail2Ban, firewall, sshpass, deploy em massa validado.

**`references/custom-wp-plugin-cutover.md`** — padrão MGS para migrar fluxo SaaS/builder/static app para plugin WordPress próprio em um site, com backup, lint remoto, WP-CLI install, import de configs, remoção segura de pastas estáticas que sombreiam rewrites, validação SMS/UTM e rollback.

**`references/openzed-chat-funnels-canary.md`** — deploy canário validado do plugin `MGS Chat Funnels` em OpenZed: upload/replace via WP Admin, ativação via REST plugins endpoint, validação de rotas `/chat/emp/br1` e `/chat/car/br1`, UTM passthrough e pitfall de JSON em `<script type="application/json">` sem `esc_html`.

**`references/chat-funnels-ad-wrapper-contract.md`** — contrato correto para anúncios nos MGS Chat Funnels: preservar `gpt.js`, wrapper JBF, `window.tags`, chamada única de `requestRewardAds()`, `showRewardedAds()` no CTA e `.ad-unit.ad`/`onInfinitePostLoaded`; não criar campos de auctions/timeout nem lógica própria de ads no plugin.

**`references/wp-plugin-json-config-render-validation.md`** — checklist para plugins com rotas públicas + admin UI: validar frontend live com DOM/JSON.parse/gate renderizado e validar admin apenas com sessão autenticada; `curl` deslogado em `/wp-admin` não prova a admin page., chamada única de `requestRewardAds()`, `showRewardedAds()` no CTA e `.ad-unit.ad`/`onInfinitePostLoaded`; não criar campos de auctions/timeout nem lógica própria de ads no plugin.

**`references/wp-plugin-json-config-render-validation.md`** — checklist para plugins com rotas públicas + admin UI: validar frontend live com DOM/JSON.parse/gate renderizado e validar admin apenas com sessão autenticada; `curl` deslogado em `/wp-admin` não prova a admin page.

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

## SEÇÃO D — SFTP para sites fora do RunCloud

Para os 4 sites AWS/Bitnami onde SFTP é o canal de acesso (read-only para verificação), ver:

**`references/sftp-sites.md`** — IPs, credenciais 1Password, arquitetura Bitnami, verificação de conectividade e pitfalls críticos.

### Sites cobertos

| Domínio | IP |
|---|---|
| openzed.com | 44.208.155.39 |
| finanzas.openzed.com | 3.19.138.131 |
| cliquet.com | 35.175.97.196 |
| finanzas.cliquet.com | 18.116.18.34 |

> **fincgriffin.com** — servidor de terceiros sem acesso programático, atualizar manualmente.

**CRÍTICO:** `wpfiles` é 100% read-only em todos os diretórios. Para escrita, usar elFinder (ver Seção B) ou SSH bitnami + .pem.

### MGS Chat Funnels — wrapper de anúncios

Para testes/instalações do plugin `MGS Chat Funnels`, ver **`references/mgs-chat-funnels-ad-wrapper-validation.md`**: rota virtual vs pasta física `index.html`, campos `company/domain`, wrapper JBF (`{company}_{domain}.builder.js`), e validação real de anúncios via `gpt.js`, `window.jbftag` e browser canário.

Para instalação em massa do `MGS Chat Funnels` junto com o plugin de quiz `activecampaign-quiz-lazy-blocks`, incluindo extração de pacote existente, RunCloud com `sudo -n`, WP Admin `/rodloguda/`, backups e validação por rota, ver **`references/mgs-chat-and-quiz-bulk-install-2026-07-03.md`**.

**Regra crítica de rollout MGS Chat Funnels:** código/plugin pode ser empacotado em comum, mas `configs/*.json` nunca são neutros. Em rollout “todos os sites”, validar e/ou ajustar individualmente por domínio antes de concluir: `ad_domain`, `route`, wrapper gerado (`{company}_{ad_domain}.builder.js`) e rota pública. Não propagar config de canário como Eggbev/OpenZed para outros sites. Se um campo admin não tiver efeito operacional real (caso confirmado: `brand`/`Site`), remover o campo e só limpar essa chave dos JSONs, sem reescrever configs inteiros.

Para mudanças na UI humana do admin do `MGS Chat Funnels`, ver `references/mgs-chat-funnels-admin-ui-taxonomy-and-rollout.md`: `Modelo de oferta` deve vir antes da identidade do chat; campos com taxonomia conhecida devem ser selects em ordem alfabética (Idioma, Vertical, País); e canário pedido pelo Rodolfo deve parar no site solicitado antes de rollout amplo.

**`references/mgs-chat-funnels-ciro-runtime-fixes-2026-07-01.md`**: correções runtime validadas com Ciro para `MGS Chat Funnels`: preload rewarded deve chamar `requestRewardAds()` 1 vez (não loop 5x), top ad precisa manter o chat no fundo via auto-scroll/observers, e deploy OpenZed via WP Admin pode exigir cookie `wordpress_test_cookie` + fluxo upload/replace quando REST plugin retorna `401 rest_cannot_view_plugin`.

Quando Ciro/JBF corrigir a regra de rewarded para “1 só”, não copie loop legado de 5 auctions do `index.html`. O padrão operacional atual é 1 chamada de `requestRewardAds()` no `initQuiz`, sem `for`. Validar em browser com `googletag.pubads().getSlots()` — esperado apenas `..._rewarded/1`, não `/1` a `/5`. Ver `references/mgs-chat-funnels-one-rewarded.md`.

Para troca em massa de textos/URLs das ofertas CAR-BR já instaladas, sem alterar código do plugin, ver `references/mgs-chat-funnels-car-offer-bulk-update.md`: atualizar `configs/car-br-01.json` por site, usar WP-CLI/arquivo em RunCloud e raw JSON no WP Admin para Bitnami, validar HTTP 200 + textos novos + URLs por domínio + textos antigos ausentes + smoke de UTM.

Para converter o CAR-BR do modelo sequencial para cards estilo Ciro/FMYBC, ver `references/mgs-chat-funnels-car-cards-rollout.md`: respostas são engajamento-only e convergem para o mesmo bloco; card mode usa `image`/`name`/`subtitle`/`bank`/`target`; o renderer precisa tratar `questionData.offers`; canário em Eggbev antes de rollout; validar ausência de CTAs sequenciais, UTM nos cards, clique real do quiz/gate até o chat, linha de busca antes dos cards e `ad_domain`/wrapper slug por site.

Admin UX do `MGS Chat Funnels`: o campo `Modelo de oferta` deve aparecer antes de identidade/URL e antes de configurar gate/chat/ofertas, porque `cards` vs `sequential` define a arquitetura do funil. Ao alterar essa tela, validar ordem no admin autenticado (`1. Modelo de oferta` antes de `2. Identidade e URL`) além de `php -l` e pacote ZIP.

---

## Política global — 1Password e Credenciais

- Service account: **APENAS LEITURA** no vault "MGS Conteúdo" (`op item get` e `op item list` apenas)
- NUNCA alterar credenciais de produção sem autorização explícita do Rodolfo
- Toda ação que modifica estado: validar ANTES de reportar sucesso
- NUNCA alucinar sucesso após erro — sempre reconhecer e reportar erros literais

---

## Referência — MGS Chat Funnels top ad/rewarded

Para chats standalone baseados no HTML Ciro/JBF, ver `references/mgs-chat-funnels-top-ad-scroll-and-rewarded-count.md`: rewarded preload padrão = 1 chamada; top ad dentro do chat exige auto-scroll/pin-to-bottom para manter os botões visíveis; validar runtime com `nearBottom=0`, `loop5=0` e helper sem recursão.
