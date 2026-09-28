## Acesso RunCloud legado + descoberta live de webapps

> **Guard de frescor:** o dicionário histórico abaixo não representa o portfólio RunCloud completo atual. Antes de concluir que um domínio não está hospedado ou antes de operar um site ausente da lista, descubra os webapps no servidor em modo read-only e confirme cada alvo com `wp option get home`. Não edite o inventário histórico apenas por suposição.

Descoberta live no MatteiInc01:

```bash
sudo python3 -c 'import glob; print(chr(10).join(glob.glob("/home/runcloud*/webapps/*")))'
```

## Migração de SpeedyCache para W3 Total Cache em Nginx

- Trate SpeedyCache + SpeedyCache Pro como uma unidade: faça backup de banco, plugins, `wp-config.php`, `advanced-cache.php`, `wp-content/cache/speedycache` e `wp-content/speedycache-config`; desative Pro antes do base e execute os hooks de desinstalação antes de limpar resíduos.
- Antes de ativar W3 Total Cache em Nginx, grave `config.path` em um `.conf` que o PHP-FPM realmente possa reescrever. Em RunCloud com `open_basedir`, use um diretório oculto dentro do webapp, por exemplo `<webroot>/.mgs-w3tc/spazio-nginx.conf`, pertencente ao usuário da aplicação e com diretório `0700`; não use caminho fora do webapp sem provar acesso pelo PHP-FPM. Exija HTTP `403`/`404` para o arquivo oculto e `404` para `/nginx.conf`.
- Não valide isso apenas por WP-CLI: o CLI pode escrever fora do `open_basedir` do PHP-FPM e esconder um aviso que aparece no painel. Execute `Root_Environment::fix_in_wpadmin()` por um probe HTTP temporário e autenticado por segredo efêmero, remova o probe em `finally` e só então declare o ambiente completo.
- Para canário conservador com Elementor, comece com page cache `file` (Disk Basic) e browser cache ativos; mantenha minify, database cache, object cache, fragment cache, **lazy load**, CDN e Varnish desativados. Defina cada opção explicitamente: configurações históricas do W3TC sobrevivem à inatividade/reinstalação e podem reativar recursos não planejados.
- Valide os assets estáticos do painel do W3TC, especialmente `pub/js/wizard.js`, `pub/css/wizard.css` e `pub/img/w3tc_cube-shadow.png`, tanto por origem quanto publicamente. Se os arquivos existirem e `wp plugin verify-checksums w3-total-cache` passar, mas o Nginx devolver `404`, preserve um manifesto de modes/owners e normalize **somente a árvore do plugin** para diretórios `0755` e arquivos `0644`; nunca aplique `chmod` global ao WordPress. Revalide checksums e todos os arquivos CSS/JS/imagens de `pub/` após a correção.
- Confirme que `wp-login.php` e `/wp-admin/` não recebem script W3TC de lazy load durante o canário. Um `lazyload.enabled=true` herdado combinado com asset inacessível pode esconder CAPTCHA/imagens e impedir login; desative, limpe o cache e valide em navegador sem contornar o CAPTCHA.
- Após o cutover, exija: SpeedyCache ausente da lista de plugins; zero opções, cron hooks, tabelas e paths exclusivos; `advanced-cache.php` identificado como W3TC; `object-cache.php` ausente salvo autorização específica; cache real gerado; home/admin/REST saudáveis; título, canonical e sinais Elementor preservados; `/nginx.conf` público em 404.
- Não use a contagem de `wp search-replace '/~prefix/'` como escopo completo quando Elementor ou RevSlider armazenam URLs em JSON. Slashes escapados e URLs protocol-relative podem ficar fora do dry-run literal. Depois do canário, compare origem e navegador, inventarie `_elementor_data` e campos JSON do RevSlider estruturalmente, separe conteúdo publicado/revisões de logs históricos e faça rollback antes de pedir nova autorização se o volume real ampliar o escopo.
- Para corrigir URLs em `_elementor_data` ou blobs RevSlider, decodifique cada JSON, substitua recursivamente somente strings dentro da estrutura, reencode e grave por chave primária em uma transação InnoDB. Exija contagens separadas de linhas/células e ocorrências, JSON válido antes/depois, zero referências no escopo e hash/contagem inalterados dos logs históricos excluídos; não use SQL textual cego nem inclua tabelas de log só para zerar um dry-run global.
- Ao restaurar CSS/fontes gerados a partir de backup, distinga arquivos totais dos realmente afetados e URLs de fonte totais das afetadas. Preserve byte a byte os CSS não afetados, normalize apenas os afetados e valide: quantidade total, quantidade afetada, substituições, arquivos de fonte existentes, hash origem/público e zero host antigo.
- Uma pasta `.DISABLED` não é órfã só pelo nome. Antes de removê-la, confirme que não aparece em `active_plugins`, não possui referência de filesystem/loader/symlink e não representa a única cópia atual; preserve rollback fora do webroot.

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

## CompanyBRS: rodapé jurídico sem copyright duplicado

O tema `companybrs-theme` pode renderizar duas superfícies simultâneas no rodapé:

1. `companybrs_disclaimer_text` — bloco de aviso/disclaimer;
2. copyright nativo — `© {year} {companybrs_footer_name/site_name}. {companybrs_footer_copy}`.

Se o novo texto jurídico já começa com `© {year} {tenant}`, não grave o parágrafo completo no disclaimer mantendo o copyright nativo: isso produz dois parágrafos públicos de copyright. O valor vazio também não desliga o copyright nativo, porque `companybrs_footer_copy()` aplica o default com `$value ?: $default`.

Procedimento seguro, sem editar arquivos do tema:

1. Validar `home`, tema ativo e idioma público; fazer backup independente de todos os theme mods relevantes por site.
2. Preservar `companybrs_footer_name`/nome do site, pois ele é o `tenantName` canônico exibido.
3. Remover do `companybrs_disclaimer_text` somente o `<p>` que contém o operador jurídico anterior; preservar o restante do aviso.
4. Gravar em `companybrs_footer_copy` somente a cauda depois de `© {year} {tenantName}.`. Se o idioma ativo usar um mod não-PT, validar primeiro o campo correspondente `companybrs_footer_copy_<lang>`.
5. Purgar o plugin de cache ativo e o object cache.
6. Validar por readback dos theme mods e por HTTP na homepage bare + cache-buster: status 200, texto jurídico exato, exatamente um parágrafo começando com `©`, e operador anterior ausente.
7. Em `ads.txt`, quando o pedido for adicionar uma linha, fazer append idempotente: preservar todas as linhas existentes, adicionar a linha exata somente se ausente e exigir contagem pública igual a 1.

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

- Ao atualizar `post_content` por `wp eval-file`/`wp_update_post()`, trate conteúdo Gutenberg/LazyBlock serializado como bytes sensíveis a escape. Passe o conteúdo por `wp_slash()` antes de `wp_update_post()`, porque o fluxo interno aplica `wp_unslash()`; sem isso, barras invertidas de atributos JSON podem ser removidas mesmo quando a troca de URL parece correta. Congele hash e contagens antes, faça readback em processo novo e exija que o resultado seja exatamente `conteúdo_original` com somente as substituições autorizadas. Se o comando mutante sair com erro, reconcilie o post e as revisões antes de repetir; nunca reaplique a troca cegamente.

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

