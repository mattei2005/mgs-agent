---
name: runcloud-api-management
description: Usa a RunCloud API v3 para operações em massa nos servidores MGS (inventário de webapps, deploy de arquivos via File Manager, etc). Cobre autenticação via 1Password, paginação, quirks da API e como cruzar inventário com documentação MGS.
tags: [runcloud, api, wordpress, infra, mass-deploy]
---

# RunCloud API Management

## Quando usar
- Preciso inventariar webapps em múltiplos servidores RunCloud
- Preciso executar operação em massa em todos os sites MGS (ex: deploy de mu-plugin)
- Preciso saber em qual servidor está um determinado site

## Credenciais

Token no 1Password — **nunca em disco, sempre em runtime**:
```bash
TOKEN=$(op item get "RunCloud API - MGS" --vault "MGS Conteúdo" --fields label=runcloud_api_key_token --reveal)
```

## API v3 — Referência rápida

- **Base URL**: `https://manage.runcloud.io/api/v3`
- **Auth**: `Authorization: Bearer $TOKEN`
- **Headers obrigatórios**: `Accept: application/json` + `Content-Type: application/json`
- **Paginação**: `?perPage=40&page=N` (máx 40 por página)
- **Rate limit**: monitorar `X-RateLimit-Remaining` no header de resposta
- **Validação**: `GET /ping` → `{"message":"pong"}` com HTTP 200

## Servidores MGS ativos

| ID | Nome |
|---|---|
| 290075 | MatteiInc01 |
| 288158 | MatteiInc02 |
| 310255 | MatteiInc03JBF |
| 266820 | SpazioVPS |
| 315018 | vpsdimelabella |

## Inventário de webapps

Script completo: `/root/mgs-agent/scripts/runcloud-inventory.sh`
JSON gerado: `/root/mgs-agent/inventario-webapps.json` (no .gitignore — infra sensível)

Para listar webapps de um servidor:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" \
  "https://manage.runcloud.io/api/v3/servers/290075/webapps?perPage=40&page=1"
```

## ⚠️ Pitfalls críticos

### 1. `primaryDomain` pode ser null na listagem
A API retorna `primaryDomain: null` para alguns webapps na listagem geral (`/webapps`).
Para obter o domínio real, chamar o endpoint de domínios individual:
```
GET /servers/{server_id}/webapps/{webapp_id}/domains
```
O inventário já faz isso — use o JSON gerado como fonte de verdade.

### 2. Token via subprocess em Python não funciona
Passar o token do shell para Python via `os.environ` e depois usar em `subprocess.run` com curl falha silenciosamente — curl recebe "Missing API Token." 
**Solução**: executar toda a lógica Python dentro do mesmo shell script que obtém o token, ou passar o token explicitamente via argumento.

### 3. Paginação — campo correto é `meta.lastPage`, não `meta.pagination.total_pages`
O script original usava `meta.pagination.total_pages` (inexistente). Campo correto: `meta.lastPage`.

### 4. Alguns sites MGS estão FORA do RunCloud
- 4 sites com SFTP direto: openzed.com, finanzas.openzed.com, cliquet.com, finanzas.cliquet.com
- 1 site em servidor de terceiros sem acesso programático: fincgriffin.com
- Para esses, ver skill `ops/sftp-deployment`

## Cruzamento inventário × documentação MGS

Ao classificar webapps para operações em massa:
1. Ler `sites.md` para lista de domínios documentados
2. Cruzar com `inventario-webapps.json` pelo campo `primary_domain`
3. Categorias: A (documentados = tocar), B (duvidosos = aguardar revisão), C (backups/pessoal/negócio local = nunca tocar)
4. **Alerta**: se B > 20% do total, documentação está desatualizada — avisar Rodolfo antes de prosseguir

### Exclusões padrão para deploys de mu-plugins em massa

Sempre excluir antes de executar:
- Sites com `deployment_mode: manual_only` (ex: `fincgriffin.com`) → manual pelo Rodolfo
- Sites SFTP (openzed.com, finanzas.openzed.com, cliquet.com, finanzas.cliquet.com) → gerenciados pela skill `wp-rest-mu-plugin-deploy`, não SSH RunCloud
- Canários já executados na fase anterior

**⚠️ Pitfall: o número "X sites" nos briefings pode estar errado.** O briefing de 24/04/2026 dizia "34 sites RunCloud" mas o inventário confirmou 26. A diferença era porque o briefing incluiu os 4 sites SFTP no cálculo. **Sempre calcular o escopo real pelo inventário antes de executar** — nunca confiar cegamente no número do briefing. Reportar discrepância ao Rodolfo antes de prosseguir se o delta for > 2 sites.

### Categoria C — padrões de exclusão automática
- Prefixo `bkp-` → backup
- Subdomínio `app.*` → aplicação, não WordPress de conteúdo
- Domínios de negócio local (limpeza, reformas, beleza, cozinha): prospectcleaning, s4blindsandshades, sunshinebeautysupplier, prospecthomeimprovement, spaziokitchensandbaths, espacolabella
- Sites pessoais/corporativos da família Mattei: jislainemattei.com, matteiservicesinc.com

## Deploy de arquivo em massa (mu-plugin, etc)

Estratégia recomendada (canário → servidor → resto):
1. Testar em 1-2 sites canário (eggbev.com + lyzmo.com) → validar resultado
2. Aplicar no servidor inteiro (ex: todos MatteiInc01)
3. Expandir para restante dos servidores

Rollback: sempre fazer backup `.bak` antes de sobrescrever:
```
arquivo_original.php → arquivo_original.php.bak
```

### ⚠️ PITFALL CRÍTICO: A API v3 NÃO suporta escrita de arquivos

A RunCloud API v3 é somente para gerenciamento de configurações (webapps, usuários, domínios).
**Não existe endpoint de upload de arquivos nem execução de scripts remotos.**
Endpoints testados e confirmados como inexistentes:
- `POST /servers/{id}/webapps/{id}/files` → 404
- `POST /servers/{id}/scripts` → 404
- `POST /servers/{id}/sshkeys` → método não suportado (GET only)
- `POST /sshkeys` → método não suportado (GET only)

### Solução para deploy de arquivos: SSH via chave

Para que Zeus (VPS MGS) possa fazer SSH nos servidores RunCloud:

**Passo único (feito uma vez por servidor, Rodolfo faz no painel RunCloud):**
1. RunCloud painel → Servidor → Settings → SSH Keys
2. Adicionar a chave pública do VPS Zeus: `/root/.ssh/id_rsa_runcloud.pub`
3. Repetir para MatteiInc01, MatteiInc02, MatteiInc03JBF

Chave gerada em: `/root/.ssh/id_rsa_runcloud` (privada) e `/root/.ssh/id_rsa_runcloud.pub` (pública)

**Após adicionar a chave, conectar com:**
```bash
ssh -i /root/.ssh/id_rsa_runcloud -o StrictHostKeyChecking=no \
  runcloud@162.55.28.178 "ls /home/runcloud/webapps/"
```

IPs dos servidores:
- MatteiInc01: 162.55.28.178 (Hetzner)
- MatteiInc02: consultar via `GET /api/v3/servers/288158`
- MatteiInc03JBF: consultar via `GET /api/v3/servers/310255`

### ⚠️ PITFALL: Porta SSH pode estar bloqueada por firewall

O RunCloud pode ter firewall que bloqueia SSH de IPs externos. Sintomas:
- `Connection refused` na porta 22
- `Connection timed out` em portas alternativas (2222, 8022, 34210)

**Diagnóstico rápido:**
```bash
for PORT in 22 222 2222 8022 34210; do
  timeout 3 bash -c "echo > /dev/tcp/IP/$PORT" 2>/dev/null && echo "ABERTA: $PORT" || echo "fechada: $PORT"
done
```

Se todas as portas estiverem fechadas: o IP do VPS (87.99.151.107) precisa ser liberado no firewall do RunCloud antes de testar SSH.

### SSH Key Vault do RunCloud (nível de conta)

O RunCloud tem um "SSH Key Vault" em Account Settings (nível de conta, não por servidor). A chave adicionada lá NÃO é aplicada automaticamente — precisa ser linkada a cada servidor individualmente:

**Processo completo para habilitar SSH do VPS Zeus nos servidores RunCloud:**

1. **Account Settings → SSH Key Vault** → adicionar chave pública do VPS
2. **Servidor → SSH → SSH Key → "Add New SSH Key"** → aba "Use vaulted SSH Key" → selecionar a chave → marcar "Add this key temporarily" (12h) → Save
   - Repetir para cada servidor (MatteiInc01, Inc02, Inc03JBF)
3. **Servidor → SSH → Config → marcar "Passwordless login" → Save Config**
   - Sem isso, o servidor exige senha mesmo com chave cadastrada
4. **Servidor → Security → Fail2Ban** → verificar se o IP do VPS (87.99.151.107) foi banido por tentativas anteriores → deletar se estiver lá
5. **Servidor → Security → Firewall** → confirmar que porta 22 está aberta (tipo "Global")

**Ordem de diagnóstico quando SSH falha:**
1. `Connection refused` → porta 22 fechada no firewall ou SSH não configurado
2. `Permission denied (publickey)` → chave não linkada ao servidor OU "Passwordless login" desativado OU IP banido no Fail2Ban
3. `Connection closed` → chave linkada mas "Passwordless login" ainda desativado

**⚠️ Pitfall: Fail2Ban bane IPs após tentativas falhas**
Se testar SSH antes de configurar corretamente (porta errada, chave errada, etc.), o Fail2Ban pode banir o IP do VPS automaticamente. Sempre verificar Fail2Ban em **Security → Fail2Ban** se a conexão subitamente parar de funcionar após tentativas.

Porém ainda requer que o firewall permita o IP de origem.

**⚠️ Pitfall: "Passwordless login" precisa ser ativado ANTES de adicionar a chave**
O RunCloud por padrão exige senha mesmo com chave pública cadastrada. Se `Permission denied (publickey)` persistir após adicionar a chave corretamente, verificar SSH → Config → Passwordless login → Save Config.

**⚠️ Pitfall: Porta 22 pode estar fechada no MatteiInc01 especificamente**
Durante testes, MatteiInc01 (162.55.28.178) retornou `Connection refused` na porta 22 enquanto Inc02 e Inc03 estavam acessíveis. Verificar Security → Firewall e confirmar que porta 22 tem regra Global TCP aberta.

**⚠️ Pitfall: Chave copiada de imagem/PDF pode ter caracteres OCR errados**
Se o usuário copia a chave de um print ou PDF (via OCR), caracteres como `l/I`, `0/O`, `rn/m` podem ser trocados silenciosamente. O SSH aceita a chave sem erro de sintaxe mas rejeita na autenticação. Sempre fornecer a chave via `cat /root/.ssh/id_rsa_runcloud.pub` direto no terminal e pedir para o usuário copiar do texto, não de imagem.

**⚠️ Pitfall: Passwordless login NÃO pode ser ativado se há crons rodando com autenticação por senha**
Rodolfo tem crons nos servidores RunCloud que dependem de autenticação por senha. Ativar "Passwordless login" no RunCloud pode interferir. Alternativa: usar usuário dedicado `zeus` com senha (criado pelo Rodolfo nos 3 servidores). Credenciais no 1Password vault "MGS Conteúdo":
- "Runcloud Server 01 - 162.55.28.178- zeus Acesso"
- "Runcloud Server 02 - 162.55.28.179- zeus Acesso"
- "Runcloud Server 03 - 46.4.95.117- zeus Acesso"
Campos: username, password, host, port.

**⚠️ Pitfall: sshpass falha com senhas que contêm caracteres especiais interpolados pelo shell**
Mesmo passando via variável (`sshpass -p "$PASS"`), o shell pode interpolar `$`, `!`, `"` antes de entregar ao sshpass. Solução robusta: usar subprocess Python sem shell=True para evitar interpolação:
```python
import subprocess, json
result = subprocess.run(['op', 'item', 'get', 'ITEM', '--vault', 'VAULT',
    '--format', 'json'], capture_output=True, text=True)
fields = {f['label']: f.get('value','') for f in json.loads(result.stdout)['fields']}
password = fields['password']
subprocess.run(['sshpass', '-p', password, 'ssh', '-o', 'PreferredAuthentications=password',
    '-o', 'PubkeyAuthentication=no', 'zeus@HOST', 'COMANDO'],
    capture_output=True, text=True)
```

**⚠️ Pitfall: Porta 22 fecha automaticamente no MatteiInc01 quando Passwordless login é revertido**
O MatteiInc01 (162.55.28.178) tem comportamento diferente dos outros servidores — a porta 22 fica inacessível (`Connection refused`) quando Passwordless login está desativado.

**⚠️ Pitfall: IP whitelist na aba "SSH Login Notifications" NÃO é firewall**
O RunCloud tem uma seção de IP whitelist dentro da aba "SSH Login Notifications" — isso controla apenas notificações de login, não acesso SSH. O firewall real está em Security → Firewall.

**⚠️ Pitfall: Fail2Ban whitelist NÃO remove bans existentes**
Adicionar o IP ao whitelist do Fail2Ban impede futuros bans, mas NÃO desbloqueia o ban atual. Se o IP já estiver banido, precisa deletá-lo manualmente na lista do Fail2Ban (Security → Fail2Ban → Delete ao lado do IP). Fazer os dois: (1) deletar ban existente + (2) adicionar ao whitelist.

**⚠️ Pitfall: Regras de firewall RunCloud precisam de "Deploy Firewall" para entrar em vigor**
Adicionar uma regra de firewall no painel RunCloud (Security → Firewall → Add New Rule) NÃO aplica imediatamente no servidor. Precisa clicar no botão "Deploy Firewall" para as regras serem enviadas ao servidor. Sem isso, a porta continua bloqueada mesmo com a regra visível no painel.

**⚠️ Pitfall: MatteiInc01 porta 22 pode ficar fechada por regra de firewall Rich**
O MatteiInc01 tinha porta 22 fechada enquanto Inc02 e Inc03 estavam abertas. Solução: adicionar regra Rich Rule no firewall do RunCloud liberando o IP `87.99.151.107` na porta 22 (Type: Rich, Protocol: TCP, Port: 22, IP: 87.99.151.107, Action: Accept) + clicar Deploy Firewall.

**Chave pública do VPS Zeus** (gerada em `/root/.ssh/id_rsa_runcloud.pub`):
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCguSHrZoHXICzWHpNKKXysWJN+eMjLtXMnVYlDoMuwa59bbKIoDHIbzBnr506sxpuJzwBfW7606uBRzX/N1QgsSOMO/T4VaPMLdpAnQY9+O/PR9utDqaG5txsvSpokg1YKUVG3BxRphTyYkdevD2GCNG9r2xPPKxUKZ+eTUlaRoI2+pFj1lSv4Zqb3o5RihboNummvC+eQKeK7byEnTyCDx32UQKFIUXbl+gkFuqhluRhjNi4nI0rUy2GDFNDxD0EqSI5Ope6RtI8TspJG2ms8kzUZedZiesg8bINGk02Qxql3aft4R6s+NrkiDv6df+1yGrcdffAGBKVnzDD1VRXfJaWMiIcO80/QlB5Y1LcfQGNQq5sRyJU264cvrtYR4keomhBUtyxT9FU4ADZN51nY2vC7i38LjeDtC6EDFAGndiMDbPW7VQ6aZiFsB/NY9TqFGyBkAS0hx9BQ8KBB9o+13BOkNdnjZewur/3rn0CfIqVTvknXJgYYQrrMXNtT3TICCqJZP7FGBIRxUIuNYYwGw/cRvejxwX0d12JGwTd+RYQSLaXyJC3Qlb8OrXr+mwlAJ2rZie9Vz7f9JbsaIhPme4f/3eIvRxE1ajmUXces3Y76YAILbi05c9LpGnxSfSBOsNXnQhsLeFALy8FKfmWf5P6OQ0iLq+acfafODq7W+w== zeus-vps-deploy
```
> ⚠️ Esta chave é temporária — Rodolfo remove do RunCloud após cada operação de deploy em massa. Não salvar nem reutilizar sem autorização explícita.

**Script de deploy após SSH configurado:**
```bash
# Para cada webapp MGS confirmado:
REMOTE_PATH="/home/runcloud/webapps/WEBAPP_NAME/wp-content/mu-plugins"
ssh -i /root/.ssh/id_rsa_runcloud runcloud@IP "mkdir -p $REMOTE_PATH"
# Backup antes de sobrescrever
ssh -i /root/.ssh/id_rsa_runcloud runcloud@IP \
  "[ -f $REMOTE_PATH/arquivo.php ] && cp $REMOTE_PATH/arquivo.php $REMOTE_PATH/arquivo.php.bak"
# Upload
scp -i /root/.ssh/id_rsa_runcloud /local/arquivo.php runcloud@IP:$REMOTE_PATH/arquivo.php
# Permissões
ssh -i /root/.ssh/id_rsa_runcloud runcloud@IP "chmod 644 $REMOTE_PATH/arquivo.php"
```

## ✅ Imagify Bulk Optimize em massa (validado em 23/04/2026)

### Estratégia híbrida: WP-CLI (RunCloud) + Browser (AWS/Bitnami)

- **27 sites RunCloud** → WP-CLI via SSH (segundos por site, sem browser)
- **4 sites AWS/Bitnami** (openzed, cliquet) → browser automation
- **fincgriffin.com** → sem acesso programático, manual

### Método: WP-CLI via SSH (RunCloud sites)

Muito mais rápido que browser. Dispara a otimização em background no WP.

```bash
sudo -u runcloud wp --path=/home/runcloud/webapps/WEBAPP_NAME imagify bulk-optimize library --allow-root 2>&1
# Retorno esperado: "Imagify bulk optimization triggered."
```

**IMPORTANTE:** Buscar senha do servidor via `terminal()` (hermes_tools), NÃO via `subprocess.run(['op', ...])` — o subprocess não tem acesso ao token de serviço do 1Password. Apenas o shell do terminal() tem.

```python
from hermes_tools import terminal
r = terminal('op item get "Runcloud Server 01 - 162.55.28.178- zeus Acesso" --vault "MGS Conteúdo" --fields label=password --reveal 2>&1')
password = r['output'].strip()
```

**Executar em paralelo por servidor** — escrever script em `/tmp/`, injetar via SSH:
```python
script = "#!/bin/bash\n"
for path, domain, user in sites:
    script += f'echo "=== {domain} ==="\n'
    script += f'sudo -u {user} wp --path={path} imagify bulk-optimize library --allow-root 2>&1 | tail -3\n'
with open('/tmp/imagify_inc01.sh', 'w') as f:
    f.write(script)

from hermes_tools import terminal
terminal(f'sshpass -p {repr(password)} ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no zeus@{ip} \'bash -s\' < /tmp/imagify_inc01.sh', timeout=600)
```

**Validação via DB (prova real de que otimizou):**
```bash
sudo -u runcloud wp --path=PATH db query \
  "SELECT COUNT(*) as total FROM wp_postmeta WHERE meta_key='_imagify_data' AND meta_value LIKE '%optimized%';" \
  --allow-root
# Se retornar número > 0 = imagens otimizadas confirmadas no banco
```

**Pitfalls críticos:**
- **Sites em `/home/runcloud2`** (ex: wantabrand, creditoparaveiculo, gamezonead) → usar `sudo -u runcloud2` em vez de `sudo -u runcloud`. Verificar dono: `ls -la /home/runcloud2/webapps/`
- **Sites sem Imagify ativo** → WP-CLI retorna `'imagify' is not a registered wp command`. Pode estar instalado mas inativo. Ativar primeiro: `sudo -u runcloud wp --path=PATH plugin install imagify --activate --allow-root`. Nos Inc03 em 23/04/2026: helixenit, infinitynexx, marevelx, vizioid, xyvlov estavam instalados mas inativos
- **Warning de mu-plugins Permission denied** (ex: lyzmo.com) → não bloqueia a otimização, apenas warning inofensivo
- **`wp imagify info` não tem saída útil** — usar query no banco (`_imagify_data`) para validar

### Método: Browser automation (sites AWS/Bitnami)

Navegar para `SITE.com/wp-admin/upload.php?page=imagify-bulk-optimization` e clicar no botão "IMAGIFY'EM ALL" / "IMAGÍFICALO TODO".

**Botão ID real:** `#imagify-bulk-action` (não confiar no texto visível — varia por idioma)
```javascript
document.getElementById('imagify-bulk-action').click();
```

**Verificar estado antes/depois:**
```javascript
JSON.stringify({
  apiDown: window.imagifyBulk?.apiDown,       // "" = ok, true = problema
  keyValid: window.imagifyBulk?.keyIsValid,   // "1" = válida
  hasBlockingError: window.imagify?.bulk?.hasBlockingError()  // false = ok
});
```

**Se `apiDown: true`:** significa que o servidor AWS não tem saída de rede para `api.imagify.io`. Verificar:
1. Configurações de rede/firewall de saída da instância EC2
2. Se a chave API está configurada em Ajustes → Imagify
3. Tentar novamente mais tarde (às vezes é falso positivo transitório)

**Se login falhar no `rodloguda`:** tentar `/wp-login.php`. Se ambos redirecionarem para 404, pode ser que a senha no WP mudou — testar `Zeus_Deploy_2024!` (senha que foi setada emergencialmente no cliquet.com em 23/04/2026). Atualizar 1Password se necessário.

---

## Verificação de campo 1Password via CLI (service account)

Para verificar o valor de um campo sem expô-lo em texto claro:

```bash
# 1. Obter o item com --reveal e salvar em arquivo temporário (nunca pipe direto para python — o token pode não ser herdado)
set -a && source /root/mgs-agent/.env && set +a
op item get 'ITEM_NAME' --reveal --vault 'MGS Conteúdo' --format json > /tmp/op_item.json

# 2. Processar em Python para comparar sem exibir o valor
python3 -c "
import json
data = json.load(open('/tmp/op_item.json'))
for f in data.get('fields', []):
    if f.get('label','').lower() == 'password':
        v = f.get('value', '')
        print(f'len={len(v)} match={v == \"VALOR_ESPERADO\"}')
        break
"
rm -f /tmp/op_item.json
```

**Pitfalls desta sequência:**
- `op item get --fields label=password` sem `--reveal` retorna texto mascarado (`[use 'op item get ID --reveal' to reveal]`) — o len fica ~65 chars (mensagem), não o valor real
- `op item get ID --reveal --format json` sem `--vault` falha com erro de service account: *"a vault query must be provided"*
- Pipe direto `op ... | python3` pode falhar se o subshell não herdar `OP_SERVICE_ACCOUNT_TOKEN` — salvar em arquivo intermediário é mais robusto
- `op item get 'ITEM_NAME'` com nome funciona, mas se quiser usar ID (ywaxe7jy...), ainda precisa `--vault`

## Política 1Password e Credenciais

### Permissões 1Password
Service account token tem APENAS LEITURA no vault "MGS Conteúdo".
- Permitido: `op item get`, `op item list`
- Bloqueado (erro 101): `op item edit`, `op item create`, `op item delete`
- Para modificar item: SOLICITAR ao Rodolfo fazer manualmente

### Alterações de Credenciais em Produção
NUNCA alterar senha/token/credencial de produção sem autorização explícita.

Fluxo obrigatório:
1. Reportar problema
2. Solicitar autorização explícita em chat
3. Aguardar resposta clara
4. Só executar após aprovação
5. Validar resultado (testar login/acesso)
6. Se envolveu 1Password, pedir atualização manual ao Rodolfo

### Validação de Ações Críticas
Toda ação que modifica estado requer validação ANTES de reportar sucesso:
- `op item edit` → executar `op item get` depois e comparar antes/depois
- Criar arquivo → `ls` ou `curl` confirmando existência
- Modificar plugin → listar estado ativo
- Alterar senha → testar login com nova senha

### Tratamento de Erros
- Sempre RECONHECER erro literal (código + mensagem)
- Sempre REPORTAR erros recebidos no relatório final
- NUNCA alucinar sucesso após erro (ex: erro 101 não é sucesso)
- NUNCA omitir falhas do relatório final

---

## ✅ Método real de deploy em massa (validado em 23/04/2026)

O deploy real dos 27 sites RunCloud foi feito via **SSH com senha + usuário `zeus`** (não via chave SSH), usando `sshpass` e um script sudo bash injetado por heredoc. Este método é mais robusto pois não requer configuração de chaves no painel RunCloud.

**Pré-requisitos:**
- Usuário `zeus` com sudo criado nos 3 servidores pelo Rodolfo
- IP do VPS (87.99.151.107) whitelisted em Security → Firewall e Security → Fail2Ban
- `sshpass` instalado no VPS Zeus: `apt install sshpass -y`
- Credenciais zeus no 1Password: "Runcloud Server 0X - IP - zeus Acesso" (vault MGS Conteúdo)

**Padrão do script de deploy por servidor:**
```python
import subprocess, json

# Carregar credenciais via 1Password CLI
result = subprocess.run(
    ['op', 'item', 'get', 'Runcloud Server 01 - 162.55.28.178- zeus Acesso',
     '--vault', 'MGS Conteúdo', '--format', 'json'],
    capture_output=True, text=True
)
fields = {f['label']: f.get('value', '') for f in json.loads(result.stdout)['fields']}
password = fields['password']  # nunca usar campos com '$' no shell — interpolar via Python

# Ler arquivos locais
with open('/root/mgs-agent/scripts/mu-plugins/hide-from-home.php') as f:
    hide_content = f.read()
with open('/root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php') as f:
    yoast_content = f.read()

# Script bash para todos os sites do servidor (injetado via heredoc)
# O script verifica /home/runcloud e /home/runcloud2, faz backup .bak antes de sobrescrever
deploy_script = """
sudo bash << 'SCRIPT'
for WEBAPP in site1 site2 site3; do
  for BASE in /home/runcloud /home/runcloud2; do
    MUDIR="$BASE/webapps/$WEBAPP/wp-content/mu-plugins"
    if [ -d "$MUDIR" ]; then
      # Backup + deploy
      [ -f "$MUDIR/hide-from-home.php" ] && cp "$MUDIR/hide-from-home.php" "$MUDIR/hide-from-home.php.bak"
      cat > "$MUDIR/hide-from-home.php" << 'EOF'
CONTEUDO_DO_ARQUIVO
EOF
      chown runcloud:runcloud "$MUDIR/hide-from-home.php"
      chmod 644 "$MUDIR/hide-from-home.php"
    fi
  done
done
SCRIPT
"""

# Executar via sshpass sem shell=True para evitar interpolação de caracteres especiais
result = subprocess.run(
    ['sshpass', '-p', password, 'ssh',
     '-o', 'PreferredAuthentications=password',
     '-o', 'PubkeyAuthentication=no',
     '-o', 'StrictHostKeyChecking=no',
     'zeus@162.55.28.178', deploy_script],
    capture_output=True, text=True, timeout=120
)
```

**Servidores implantados com sucesso:**
- MatteiInc01 (162.55.28.178): 15 sites ✅
- MatteiInc02 (162.55.28.179): 2 sites ✅  
- MatteiInc03JBF (46.4.95.117): 8 sites ✅

**⚠️ Pitfall: alguns webapps ficam em `/home/runcloud2` em vez de `/home/runcloud`**
Ex: `wantabrand` está em `/home/runcloud2/webapps`. O script deve checar ambos os caminhos.

**⚠️ Pitfall CRÍTICO: usuário `zeus` NÃO tem permissão de leitura/escrita em `/home/runcloud/`**
`ls /home/runcloud/webapps/` retorna `Permission denied`. Todo acesso a arquivos nos webapps requer `sudo`.
Consequência: verificação de diretório (`[ -d "$MUDIR" ]`) e escrita de arquivos via SCP direto falham silenciosamente.
Solução robusta: SCP para `/tmp/` (zeus tem acesso) → `sudo mv` para destino:
```bash
# SCP para /tmp
sshpass -p "$PASS" scp $SSH_OPTS "$LOCAL_FILE" "zeus@$IP:/tmp/arquivo.php"
# sudo mv para destino + permissões
sshpass -p "$PASS" ssh $SSH_OPTS zeus@$IP \
  "echo '$PASS' | sudo -S bash -c 'mv /tmp/arquivo.php $MUDIR/arquivo.php && chmod 644 $MUDIR/arquivo.php && chown runcloud:runcloud $MUDIR/arquivo.php && echo MOVED'"
# sudo md5sum para verificar
REMOTE_MD5=$(sshpass -p "$PASS" ssh $SSH_OPTS zeus@$IP \
  "echo '$PASS' | sudo -S md5sum '$MUDIR/arquivo.php' 2>/dev/null | awk '{print \$1}'")

**⚠️ Pitfall: Remover chave SSH do RunCloud vault após operação**
A chave `zeus-vps-deploy` em `/root/.ssh/id_rsa_runcloud` deve ser removida do vault RunCloud após deploy concluído. Não deixar chave permanente por segurança (decisão do Rodolfo).
