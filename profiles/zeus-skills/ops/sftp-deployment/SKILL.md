---
name: sftp-deployment
description: Deploy de arquivos via SFTP direto para sites MGS que estão fora do RunCloud (openzed.com, finanzas.openzed.com, cliquet.com, finanzas.cliquet.com). Credenciais no 1Password vault "MGS Conteúdo".
tags: [sftp, wordpress, deploy, infra, mass-deploy]
---

# SFTP Deployment — Sites fora do RunCloud

## Quando usar
- Preciso fazer deploy de arquivo (mu-plugin, script, config) nos 4 sites MGS que ficam fora do RunCloud
- RunCloud API não alcança esses sites

## Sites cobertos por esta skill

| Domínio | Item 1Password | IP |
|---|---|---|
| openzed.com | `SFTP openzed servers` | 44.208.155.39 |
| finanzas.openzed.com | `SFTP finanzas.openzed servers` | 3.19.138.131 |
| cliquet.com | `SFTP cliquet servers` | 35.175.97.196 |
| finanzas.cliquet.com | `SFTP finanzas.cliquet servers` | 18.116.18.34 |

> **fincgriffin.com** está em servidor de terceiros sem acesso programático — atualizar manualmente via File Manager do WP Admin quando necessário.

## Arquitetura dos servidores (CRÍTICO)

Estes 4 sites são instâncias **AWS EC2 com stack Bitnami WordPress**, NÃO RunCloud.

- Webroot real: `/opt/bitnami/wordpress/`
- O usuário SFTP `wpfiles` conecta em `/opt/bitnami/wordpress/` como diretório inicial — confirmado via `pwd` em 2026-04-25
- O `ls` mostra `wp-admin`, `wp-content`, `wp-config.php`, etc. — mas os **paths absolutos dentro da sessão SFTP são `/opt/bitnami/wordpress/wp-content/...`**, não paths relativos
- **`wpfiles` é COMPLETAMENTE READ-ONLY** — consegue navegar/listar/baixar (`get`) mas **não escreve em nenhum diretório** (`put`, `mkdir`, `rename` → Permission denied em todos, incluindo `wp-content/`, `wp-content/mu-plugins/`, `wp-content/uploads/`, etc.)
- O usuário com acesso de escrita é `bitnami`, autenticado por **chave `.pem`** gerada na criação da instância EC2
- Não há acesso Shell — SSH com `wpfiles` retorna `"This service allows sftp connections only."`

## Estrutura das credenciais no 1Password

Cada item contém:
- `protocol` — método de conexão (sftp)
- `host` — IP do servidor
- `port` — porta SSH (22)
- `wpfiles` — **é o nome do usuário E é o label do campo onde está a senha**. O campo username do item está vazio — ignorar. Usar `wpfiles` como username. A senha está no campo de mesmo nome `wpfiles`.

Buscar credenciais:
```bash
HOST=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields host --reveal)
PORT=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields port --reveal)
PASS=$(op item get "SFTP openzed servers" --vault "MGS Conteúdo" --fields wpfiles --reveal)
```

## Como fazer deploy (quando tiver acesso de escrita)

### Pré-requisito: `mu-plugins` deve existir
O diretório `wp-content/mu-plugins/` **não existe por padrão** nestes servidores — precisa ser criado antes do primeiro deploy. Como `wpfiles` não tem permissão de escrita, há três opções:

**Opção A — Via SSH com chave .pem (usuário bitnami):**
```bash
ssh -i /caminho/chave.pem bitnami@$HOST \
  "mkdir -p /opt/bitnami/wordpress/wp-content/mu-plugins && chmod 755 /opt/bitnami/wordpress/wp-content/mu-plugins"
```

**Opção B — Plugin temporário via WP REST API (RECOMENDADO quando não há .pem):**
Ver skill `wp-rest-mu-plugin-deploy`. Instala plugin ZIP via REST, ele cria o diretório e escreve os arquivos via PHP, depois se auto-deleta.

**Opção C — Manual via WP Admin (WP File Manager plugin):**
1. Instalar plugin "WP File Manager" (mstw/wp-file-manager ou wp-file-manager-pro)
2. Plugins → File Manager → navegar para `wp-content/`
3. Criar pasta `mu-plugins`
4. Criar arquivos PHP dentro dela

> ⚠️ **PITFALL CRÍTICO de backslash**: ao criar/editar arquivos PHP via elFinder (WP File Manager), qualquer string PHP com backslashes — como namespaces (`'Yoast\\WP\\SEO'`) — tem os backslashes **duplicados** durante o transit JavaScript. O arquivo chega no servidor com `'Yoast\\\\WP\\\\SEO'` (PHP inválido e fatal). **Workarounds:**
> - Usar o editor embutido do WP File Manager (duplo-clique no arquivo) para colar o conteúdo — o editor interno não sofre o mesmo escaping duplo
> - Ou deletar o arquivo corrompido e recriar via `console` do browser com o conteúdo codificado em base64
> - ⚠️ Depois de criar, sempre verificar o arquivo via SFTP read-only: `grep "Yoast\\\\" arquivo.php` — deve retornar `Yoast\\WP\\SEO` com apenas 1 backslash entre segmentos, não 2

### Upload via SFTP (após diretório criado):
```bash
sshpass -p "$PASS" sftp -P "$PORT" \
  -o StrictHostKeyChecking=no \
  -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no \
  wpfiles@$HOST << EOF
put /caminho/local/arquivo.php wp-content/mu-plugins/arquivo.php
ls wp-content/mu-plugins
EOF
```

> Notar: o path é **relativo** (`wp-content/mu-plugins/`) porque o SFTP já conecta na raiz do WP. NÃO usar `/opt/bitnami/wordpress/wp-content/...`.

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

## Pitfalls — CRÍTICOS para sites Bitnami SFTP-only

### wpfiles é completamente read-only
O usuário SFTP `wpfiles` nos sites Bitnami (openzed, cliquet) tem permissão apenas de leitura. `put` retorna `Permission denied` em TODOS os diretórios (mu-plugins/, plugins/, uploads/). Não há forma de escrever via SFTP.

### Método WPCode Snippet — RISCO DE FATAL ERROR (⚠️ preferir elFinder sempre)
Deploy via WPCode snippet PHP funciona (validado em finanzas.openzed.com e finanzas.cliquet.com) MAS é o método de **maior risco** em Bitnami sem acesso .pem:
- Parse error no PHP = site 100% DOWN irrecuperável sem AWS Console
- **Incidente real:** 2026-04-25 openzed.com ficou DOWN por b64 corrompido neste método. Recuperação exigiu dev externo + AWS Console (indisponível a 3h46 EDT fim de semana).
- **Sempre preferir elFinder `cmd: put`** — escreve o arquivo em disco sem executar PHP, portanto parse error no conteúdo não derruba o site.
- Usar WPCode apenas se elFinder indisponível E horário comercial E dev externo acessível.

Se WPCode for inevitável:
- O b64 do conteúdo PHP DEVE ser gerado diretamente do arquivo canonical: `base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php`
- **NUNCA editar o b64 manualmente** — qualquer typo (ex: `'key'2`) causa PHP parse error → site 100% DOWN
- WPCode inclui snippets PHP ativos via include() — parse error quebra todo o site
- Sessões WP nos servidores Bitnami expiram em ~5 minutos — trabalhar rápido

### Recuperação de site DOWN por snippet WPCode (Bitnami)
Se site entrar em down por snippet PHP inválido e SFTP for read-only:
1. Único caminho: acesso MySQL direto
2. Via AWS console ou bitnami SSH (porta 22, usuário `bitnami`, chave .pem)
3. Query de recovery: `UPDATE <db>.wp_posts SET post_status='draft' WHERE post_type='wpcode' AND post_title='<snippet_title>';`
4. Reiniciar Apache/PHP-FPM se necessário: `sudo /opt/bitnami/ctlscript.sh restart apache`
5. WP REST API fica 500 durante o fatal error — não há como remover o snippet via API

### Sessão WP Admin expira rápido
Sessão WP expira em ~5 min. Ao trabalhar com snippets, ter o JS de injeção pronto ANTES de entrar no admin. Não copiar/montar o b64 depois de entrar na sessão.

## Pitfalls

- **`wpfiles` é read-only** (confirmado em 23/04/2026): consegue listar/navegar mas **não criar diretórios nem fazer upload**. Para escrita real, precisa da chave `.pem` do EC2 + usuário `bitnami`.
- **`mkdir` via SFTP falha com "Permission denied"** mesmo que o `ls` funcione — não confundir capacidade de leitura com escrita.
- **SSH interativo bloqueado**: estes servidores retornam `"This service allows sftp connections only."` ao tentar SSH shell com `wpfiles`. Apenas SFTP funciona com esse usuário.
- **Path ABSOLUTO no SFTP**: o usuário conecta em `/opt/bitnami/wordpress/` mas o `pwd` retorna esse path completo. Usar o path absoluto `/opt/bitnami/wordpress/wp-content/mu-plugins/arquivo.php` — confirmado em 2026-04-25. O `ls` de path relativo (`ls wp-content/mu-plugins/`) pode retornar "not found"; usar path absoluto.
- **`wpfiles` é 100% read-only em TODOS os diretórios** — confirmado em 2026-04-25: `put` falha em `mu-plugins/`, `wp-content/`, `wp-content/uploads/`, em todos. `rename` também falha. Não há nenhum diretório com escrita para esse usuário.
- **`mu-plugins` não existe por padrão** nestes servidores Bitnami — criar antes do primeiro deploy.
- **StrictHostKeyChecking=no** necessário na primeira conexão para não travar em prompt interativo.

## Verificação de conectividade
```bash
# Testar porta 22 aberta
for IP in 44.208.155.39 3.19.138.131 35.175.97.196 18.116.18.34; do
  timeout 3 bash -c "echo > /dev/tcp/$IP/22" 2>/dev/null && echo "ABERTA: $IP" || echo "FECHADA: $IP"
done

# Listar raiz do WordPress via SFTP (confirma credenciais)
sshpass -p "$PASS" sftp -P 22 -o StrictHostKeyChecking=no wpfiles@$HOST << 'EOF'
ls
ls wp-content
EOF
```

## Verificação pós-deploy
```bash
sshpass -p "$PASS" sftp -P 22 -o StrictHostKeyChecking=no wpfiles@$HOST << 'EOF'
ls wp-content/mu-plugins
EOF
```
