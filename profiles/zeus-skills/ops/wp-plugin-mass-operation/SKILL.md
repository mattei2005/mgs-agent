---
name: wp-plugin-mass-operation
description: "Operações WordPress em massa nos 31 sites MGS: WP-CLI (RunCloud SSH), browser automation (AWS/Bitnami), SFTP, elFinder/WPCode deploy de mu-plugins, e RunCloud API v3. Cobre infra completa (27 RunCloud + 4 Bitnami + fincgriffin), credenciais, 1Password, SSH setup e pitfalls críticos de deploy."
tags: [wordpress, wp-cli, plugin, mass-operation, runcloud, sftp, mu-plugins, bitnami, api, deploy, infra]
related_skills: [mgs-infra-inventory, log-monitor-discord-alert, shell-cron-env-export]
---

# Operações de Plugin WordPress em Massa — Sites MGS

## Quando usar
- Preciso instalar, ativar, desativar ou deletar um plugin em todos os 31 sites
- Preciso rodar um comando WP-CLI de plugin (ex: imagify bulk-optimize, yoast reindex) em massa
- Preciso verificar se um plugin está instalado/ativo em todos os sites
- Recebeu REPORT-INFRA de um agente e precisa atualizar o inventário de infra
- Auditoria da operação MGS (o que existe, onde, quem criou)
- Onboarding de novo agente — verificar o que já existe

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

---

## Política global — 1Password e Credenciais

- Service account: **APENAS LEITURA** no vault "MGS Conteúdo" (`op item get` e `op item list` apenas)
- NUNCA alterar credenciais de produção sem autorização explícita do Rodolfo
- Toda ação que modifica estado: validar ANTES de reportar sucesso
- NUNCA alucinar sucesso após erro — sempre reconhecer e reportar erros literais
