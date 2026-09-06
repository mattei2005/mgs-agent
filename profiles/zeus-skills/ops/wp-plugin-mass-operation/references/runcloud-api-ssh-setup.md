# RunCloud API v3 + SSH Setup

Conteúdo originalmente em skill `runcloud-api-management` (arquivada 2026-05-06).

## RunCloud API v3 — Referência rápida

- **Base URL**: `https://manage.runcloud.io/api/v3`
- **Auth**: `Authorization: Bearer $TOKEN`
- **Token**: `op item get "RunCloud API - MGS" --vault "MGS Conteúdo" --fields label=runcloud_api_key_token --reveal`
- **Headers obrigatórios**: `Accept: application/json` + `Content-Type: application/json`
- **Paginação**: `?perPage=40&page=N` (máx 40 por página); campo correto é `meta.lastPage` (não `meta.pagination.total_pages`)
- **Validação**: `GET /ping` → `{"message":"pong"}`

### ⚠️ A API v3 NÃO suporta escrita de arquivos
Endpoints testados como inexistentes: `POST /servers/{id}/webapps/{id}/files`, `POST /servers/{id}/scripts`.
Deploy de arquivos = SSH com `sshpass` + usuário `zeus` com sudo.

## Servidores MGS ativos

| ID | Nome | IP |
|---|---|---|
| 290075 | MatteiInc01 | 162.55.28.178 |
| 288158 | MatteiInc02 | 162.55.28.179 |
| 310255 | MatteiInc03JBF | 46.4.95.117 |
| 266820 | SpazioVPS | — |
| 315018 | vpsdimelabella | — |

## Inventário de webapps

Script: `/root/mgs-agent/scripts/runcloud-inventory.sh`
JSON: `/root/mgs-agent/inventario-webapps.json` (no .gitignore)

### Preflight de aplicações custom/Node no MatteiInc01

- Para validar Nginx no MatteiInc01, usar `sudo -n /usr/local/sbin/nginx-rc -t`; `nginx` e `/usr/sbin/nginx-rc` não são os caminhos canônicos. Um erro de caminho/sudo nesse teste não prova falha do serviço.
- GET de detalhe do servidor pode retornar objeto direto, enquanto listas usam `data`; resolver `payload.get('data', payload)` antes de ler campos.
- Paginação deve aceitar `meta.lastPage` e `meta.pagination.total_pages` conforme o endpoint/resposta e validar contagens.
- Aplicações Node exigem webapp custom e proxy para processo local; conferir a versão exigida pelo projeto antes de publicar e não substituir o Node global dos sites como atalho.

### Pitfalls da API
1. `primaryDomain` pode ser `null` na listagem — chamar `/webapps/{id}/domains` para domínio real
2. Paginação usa `meta.lastPage`, não `meta.pagination.total_pages`

---

## Setup SSH para deploy (usuário zeus)

Pré-requisitos (configurados uma vez pelo Rodolfo):
- Usuário `zeus` com sudo criado nos 3 servidores
- Egress público da VPS de produção atual validado no momento da operação e whitelisted em Security → Firewall e Security → Fail2Ban; nunca reutilizar IP estático de VPS desativada ou reassigned
- Antes de alterar whitelist, auditar por readback todos os três servidores. Remover IP aposentado e adicionar o egress atual são mudanças de firewall separadas, sujeitas à confirmação crítica e a novo readback após `Deploy Firewall`
- `sshpass` instalado: `apt install sshpass -y`

Credenciais: `op item get "Runcloud Server 0X - IP- zeus Acesso" --vault "MGS Conteúdo" --fields label=password --reveal`

### Ordem de diagnóstico quando SSH falha
1. `Connection refused` → porta 22 fechada no firewall
2. `Permission denied (publickey)` → chave não linkada OU Passwordless login desativado OU Fail2Ban ban
3. `Connection closed` → Passwordless login desativado

### Pitfalls SSH críticos
- **Fail2Ban NÃO remove bans existentes ao adicionar whitelist** — deletar o ban atual em Security → Fail2Ban, depois adicionar ao whitelist
- **Regras de firewall RunCloud precisam de "Deploy Firewall"** — sem o clique, porta continua bloqueada
- **MatteiInc01 porta 22 fecha quando Passwordless login é revertido** — comportamento único desse servidor
- **sshpass falha com senhas contendo caracteres especiais interpolados pelo shell** — usar `subprocess.run` sem `shell=True`:
  ```python
  subprocess.run(['sshpass', '-p', password, 'ssh', '-o', 'PreferredAuthentications=password',
      '-o', 'PubkeyAuthentication=no', 'zeus@HOST', 'COMANDO'], capture_output=True, text=True)
  ```
- **Usuário `zeus` NÃO tem permissão de leitura em `/home/runcloud/`** — todo acesso exige `sudo`
- **Alguns sites ficam em `/home/runcloud2/`** (ex: wantabrand, creditoparaveiculo, gamezonead) — verificar: `ls -la /home/runcloud2/webapps/`

---

## Deploy em massa validado (23/04/2026)

Método: SSH com senha + usuário `zeus` + script sudo bash injetado via heredoc.

```python
import subprocess, json
from hermes_tools import terminal

# Buscar senha via terminal (NÃO subprocess — subprocess não acessa token 1P)
r = terminal('op item get "Runcloud Server 01 - 162.55.28.178- zeus Acesso" --vault "MGS Conteúdo" --fields label=password --reveal 2>&1')
password = r['output'].strip()

# Script para injetar via SSH
deploy_script = """
sudo bash << 'SCRIPT'
for WEBAPP in site1 site2; do
  for BASE in /home/runcloud /home/runcloud2; do
    MUDIR="$BASE/webapps/$WEBAPP/wp-content/mu-plugins"
    if sudo test -d "$MUDIR"; then
      sudo cp "$MUDIR/arquivo.php" "$MUDIR/arquivo.php.bak" 2>/dev/null || true
      sudo tee "$MUDIR/arquivo.php" > /dev/null << 'EOF'
CONTEUDO_DO_ARQUIVO
EOF
      sudo chmod 644 "$MUDIR/arquivo.php"
      sudo chown runcloud:runcloud "$MUDIR/arquivo.php" 2>/dev/null || sudo chown runcloud2:runcloud2 "$MUDIR/arquivo.php"
    fi
  done
done
SCRIPT
"""

result = subprocess.run(
    ['sshpass', '-p', password, 'ssh',
     '-o', 'PreferredAuthentications=password',
     '-o', 'PubkeyAuthentication=no',
     '-o', 'StrictHostKeyChecking=accept-new',
     '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts_mgs',
     'zeus@162.55.28.178', deploy_script],
    capture_output=True, text=True, timeout=120
)
```

Servidores com deploy validado:
- MatteiInc01 (162.55.28.178): 15 sites ✅
- MatteiInc02 (162.55.28.179): 2 sites ✅
- MatteiInc03JBF (46.4.95.117): 8 sites ✅

---

## Imagify Bulk Optimize em massa (validado 23/04/2026)

```bash
sudo -u runcloud wp --path=/home/runcloud/webapps/WEBAPP_NAME imagify bulk-optimize library --allow-root 2>&1
# Retorno esperado: "Imagify bulk optimization triggered."
```

**Pitfalls Imagify:**
- Sites em `/home/runcloud2` → usar `sudo -u runcloud2`
- Plugin instalado mas inativo → ativar: `wp plugin install imagify --activate --allow-root`
- `wp imagify info` não tem saída útil — validar via DB:
  ```sql
  SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='_imagify_data' AND meta_value LIKE '%optimized%';
  ```
- `apiDown: true` no Bitnami → site AWS sem saída para `api.imagify.io`

---

## Cruzamento inventário × documentação MGS (validação antes de mass operation)

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

**⚠️ Nunca confiar no número do briefing** — briefing 24/04/2026 dizia "34 sites RunCloud", inventário confirmou 26. Sempre calcular escopo pelo inventário.

### Exclusões padrão
- Prefixo `bkp-` → backup
- Domínios de negócio local (limpeza, reformas, etc.)
- Sites pessoais/corporativos família Mattei
- Sites SFTP (gerenciados separadamente)

---

## Verificação de campos 1Password via CLI

```bash
set -a && source /root/mgs-agent/.env && set +a
op item get 'ITEM_NAME' --reveal --vault 'MGS Conteúdo' --format json > /tmp/op_item.json
python3 -c "
import json
data = json.load(open('/tmp/op_item.json'))
for f in data.get('fields', []):
    if f.get('label','').lower() == 'password':
        v = f.get('value', '')
        print(f'len={len(v)}')
        break
"
rm -f /tmp/op_item.json
```

**Pitfalls 1Password:**
- `op item get --fields label=X` sem `--reveal` retorna texto mascarado (~65 chars), não o valor real
- `op item get` sem `--vault` falha com service account: *"a vault query must be provided"*
- `os.environ` em `execute_code` NÃO propaga para `terminal()` subprocessos — chamar `terminal('op item get ...')` diretamente
