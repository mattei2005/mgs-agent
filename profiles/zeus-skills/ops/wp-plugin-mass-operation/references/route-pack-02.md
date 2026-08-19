## Acesso RunCloud legado + descoberta live de webapps

> **Guard de frescor:** o dicionário histórico abaixo não representa o portfólio RunCloud completo atual. Antes de concluir que um domínio não está hospedado ou antes de operar um site ausente da lista, descubra os webapps no servidor em modo read-only e confirme cada alvo com `wp option get home`. Não edite o inventário histórico apenas por suposição.

Descoberta live no MatteiInc01:

```bash
sudo python3 -c 'import glob; print(chr(10).join(glob.glob("/home/runcloud*/webapps/*")))'
```

Alvos validados em produção em 2026-08-19:

```text
vagaaqui.com              /home/runcloud/webapps/vagaaqui                    runcloud
newsfolha.com             /home/runcloud/webapps/newsfolha                   runcloud
jobs.newsfolha.com        /home/runcloud/webapps/newsfolha-jobs              runcloud
financescredit.com        /home/runcloud/webapps/financescredit              runcloud
deolhonoworld.com         /home/runcloud/webapps/deolho                      runcloud
jobs.deolhonoworld.com    /home/runcloud2/webapps/jobs-deolhonoworld-com     runcloud2
noticiainforme.com        /home/runcloud/webapps/noticiainforme              runcloud
esp.noticiainforme.com    /home/runcloud/webapps/esp-noticiainforme          runcloud
scorexboost.com           /home/runcloud/webapps/scorexboost                 runcloud
jobs.scorexboost.com      /home/runcloud/webapps/sscorexboost-jobs           runcloud
```

Para validar um alvo descoberto:

```bash
sudo -u <owner> wp --path=<root_path> option get home --allow-root
```

## Dicionário histórico de 27 sites

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
        # Montar script remoto sem credenciais.
        lines = "#!/bin/bash\n"
        for path, domain, user in config['sites']:
            cmd = wp_command_template.format(path=path, user=user)
            lines += f'echo "=== {domain} ==="\n{cmd} 2>&1 | tail -3\n'

        script_path = f"/tmp/wpcli_{ip.replace('.', '_')}.sh"
        with open(script_path, 'w') as f:
            f.write(lines)

        # Resolver a senha dentro do shell, redirecionar para arquivo 600 e usar
        # sshpass -f. O valor não entra em argv, stdout nem no contexto do agente.
        shell = f'''set -euo pipefail
set -a
source /root/mgs-agent/.env
set +a
pw_file=$(mktemp)
chmod 600 "$pw_file"
trap 'rm -f "$pw_file"' EXIT
op item get "{config["op_item"]}" --vault "MGS Conteúdo" --fields label=password --reveal > "$pw_file"
sshpass -f "$pw_file" ssh -o PreferredAuthentications=password \\
  -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new \\
  -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs \\
  zeus@{ip} 'bash -s' < {script_path}
'''
        result = terminal(shell, timeout=600)
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

**Credenciais AWS sites — títulos canônicos no 1Password:**
| Site | Item 1Password |
|---|---|
| finanzas.openzed.com | `Wordpress - finanzas.openzed.com` |
| openzed.com | `Wordpress - openzed.com` |
| finanzas.cliquet.com | `Wordpress - finanzas.cliquet.com` |
| cliquet.com | `Wordpress - cliquet.com` |

Nunca registrar ou repetir senha de login/application password nesta skill. Resolver os campos no 1Password em runtime e manter os valores fora de argv/stdout. Para REST autenticado, os itens atuais expõem `api_auth_user` + `api_application_password`; `cliquet.com` usa `username` + `wp_app_password`. Se houver títulos duplicados, localizar por `op item list`, selecionar o UUID validado e fazer smoke read-only por post ID; sucesso só após HTTP 200 sem imprimir credenciais.

---

## ⚠️ Pitfalls

1. **`sudo -u runcloud` falha em sites do runcloud2** — wantabrand (Inc01), creditoparaveiculo e gamezonead (Inc02) estão em `/home/runcloud2/` e pertencem ao usuário `runcloud2`. Usar `sudo -u runcloud2`. Verificar com `ls -la /home/runcloud2/webapps/`.

2. **Plugin instalado mas inativo** — WP-CLI retorna `'X' is not a registered wp command` se plugin está instalado mas inativo. Sempre rodar `plugin install SLUG --activate` (o `--activate` é ignorado se já estiver ativo, mas ativa se estiver inativo).

3. **Subprocess Python não acessa 1Password** — `subprocess.run(['op', 'item', 'get', ...])` retorna vazio/erro porque o subprocess não herda o token de serviço do ambiente. Usar sempre `terminal('op item get ...')` do hermes_tools.

4. **Warning "Permission denied" em mu-plugins** — alguns sites (lyzmo.com) mostram warning de permissão ao rodar WP-CLI. Não bloqueia a operação — ignorar.

5. **`wp imagify info` não tem output útil** — usar query no banco `_imagify_data` para validação real.

6. **`apiDown: true` no browser Imagify** — a API do Imagify é externa. Se o servidor AWS/Bitnami não tiver saída para `api.imagify.io`, o bulk não dispara pelo browser. Verificar `window.imagifyBulk.apiDown` no console.

---

