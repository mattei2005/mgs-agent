---
name: wp-plugin-mass-operation
description: Executa operações de plugin WordPress em massa nos 31 sites MGS via WP-CLI (RunCloud) + browser automation (AWS/Bitnami). Cobre install, activate, deactivate, delete e comandos WP-CLI específicos de plugin.
tags: [wordpress, wp-cli, plugin, mass-operation, runcloud, infra]
related_skills: [runcloud-api-management, wp-rest-mu-plugin-deploy, sftp-deployment]
---

# Operações de Plugin WordPress em Massa — Sites MGS

## Quando usar
- Preciso instalar, ativar, desativar ou deletar um plugin em todos os 31 sites
- Preciso rodar um comando WP-CLI de plugin (ex: imagify bulk-optimize, yoast reindex) em massa
- Preciso verificar se um plugin está instalado/ativo em todos os sites

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
            f'-o PubkeyAuthentication=no -o StrictHostKeyChecking=no '
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
