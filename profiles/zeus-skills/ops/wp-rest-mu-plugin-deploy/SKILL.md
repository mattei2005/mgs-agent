---
name: wp-rest-mu-plugin-deploy
description: "Deploy de arquivos PHP em wp-content/mu-plugins/ via WP File Manager (elFinder) + base64. Método validado para servidores Bitnami/AWS sem SSH de escrita. Inclui install/remove do File Manager via REST API."
tags: [wordpress, rest-api, mu-plugins, deploy, bitnami, infra, elfinder]
related_skills: [sftp-deployment]
---

# Deploy de mu-plugins via WP File Manager + elFinder

## PITFALL FATAL #1 — NUNCA inventar b64 (LEIA ANTES DE QUALQUER DEPLOY)

**Esta regra existe antes de qualquer instrução desta skill.**

Antes de qualquer deploy que envolva b64 de arquivo PHP:

```bash
# 1. GERAR — sempre via shell, nunca escrever manualmente
b64=$(base64 -w 0 /caminho/arquivo.php)

# 2. VALIDAR reverso — MD5 deve bater com o original
[ "$(echo "$b64" | base64 -d | md5sum | awk '{print $1}')" = \
  "$(md5sum /caminho/arquivo.php | awk '{print $1}')" ] && echo "OK" || echo "FALHOU — NÃO PROSSEGUIR"

# 3. Só após "OK" → usar $b64 no snippet/payload
```

**Se o b64 não foi gerado por shell e validado por MD5 reverso — NÃO PROSSEGUIR.**

> **Caso histórico:** openzed.com 2026-04-25 — Zeus inventou um b64 "made-up" em vez de executar `base64 -w 0`. O PHP gerado tinha `'key'2` na linha 79. Site DOWN por 18+ horas, dependência de dev externo para recuperar. Ver SOUL.md case study Zeus 2026-04-25.

---

## Quando usar
- Servidor sem SSH de escrita (Bitnami/AWS com usuário SFTP `wpfiles` read-only na raiz)
- Sem chave `.pem` EC2 disponível
- Credenciais WP Admin (`username` + `password`) e Application Password disponíveis
- Precisa criar `wp-content/mu-plugins/` e escrever arquivos PHP nele

## Quando NÃO usar
- Servidor com acesso SSH/sudo (RunCloud) — usar deploy direto via SSH
- Site sem credenciais admin disponíveis

---

## TEMPLATE CANÔNICO DO SNIPPET PHP (OBRIGATÓRIO — nunca reescrever)

O arquivo `/root/.hermes/profiles/zeus/skills/ops/wp-rest-mu-plugin-deploy/templates/wpcode-snippet-template.php` contém o template PHP canônico do snippet WPCode.

**Regra:** Nunca reescrever ou regenerar o snippet PHP a cada sessão. Copiar literalmente do template, substituindo apenas `${B64_PAYLOAD}` pelo output de `base64 -w 0 yoast-rest-meta.php` (após validação MD5 reversa obrigatória).

Motivo: cada instância LLM que reescreve o snippet introduz variações de estilo (multi-linha vs inline, com/sem comentários, nomes de variáveis diferentes) e — mais crítico — pode esquecer o cleanup. O template fixo elimina ambos os riscos.

---

## ⚠️ POLÍTICA DE ESCOLHA DE MÉTODO (CRÍTICO — ler antes de executar)

Esta skill documenta **dois** métodos para deploy em Bitnami/AWS sem SSH de escrita:

| Método | Risco | Quando usar |
|---|---|---|
| **elFinder `cmd: put`** | ✅ Baixo | **Sempre preferido.** Escreve o arquivo em disco via File Manager — o PHP não é executado na escrita. Parse error no conteúdo = arquivo corrompido, site continua UP. |
| **WPCode snippet** | ❌ Alto | Última opção. WPCode inclui o PHP via `include()` no carregamento do WP — parse error = **fatal error imediato = site 100% DOWN**. |

### Regra absoluta para sites Bitnami sem chave .pem

> **Nunca usar WPCode snippet para arquivos PHP quando não há acesso SSH/chave .pem disponível para recuperação.**
> Se o snippet tiver parse error e o site cair, a única recuperação é AWS Console ou chave bitnami.
> elFinder `cmd: put` não tem esse risco — usar sempre.

### Validação MD5 reversa obrigatória ANTES de ativar snippet WPCode

Se por algum motivo WPCode snippet for necessário, validar antes de ativar:

```bash
# 1. Gerar b64 fresco do arquivo canônico (NUNCA editar manualmente)
B64=$(base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php)

# 2. Decodificar e verificar MD5 localmente
echo "$B64" | base64 -d | md5sum
# Comparar com MD5 esperado: 069270de4c07a9d15838ff45df65f539

# 3. Se MD5 divergir: NÃO prosseguir. Regerar o b64.
# 4. Apenas se MD5 bater: colar no snippet e ativar.
```

**Nunca pular esta validação.** Um typo (caractere extra, cópia parcial, versão errada do arquivo) gera PHP inválido → site DOWN.

### Restrição de horário para WPCode snippet

**Nunca executar deploy via WPCode snippet em sites Bitnami após meia-noite** sem confirmação explícita do Rodolfo para o horário. Se dev externo estiver indisponível (fim de semana, madrugada), adiar para horário comercial.

### Sobre inércia de sessão

Evitar raciocínio do tipo *"usamos WPCode na sessão anterior, então é o método"*. Sempre avaliar qual método é **mais seguro para o estado atual do site**:
- `mu-plugins/` já existe + arquivo já lá → elFinder `cmd: put` no hash existente (mais simples, sem risco)
- `mu-plugins/` não existe → elFinder `mkdir` + `mkfile` + `put` (ainda mais seguro que WPCode)
- WPCode → apenas se elFinder indisponível + horário comercial + dev externo acessível

---

---

## Credenciais dos 4 sites SFTP MGS

Items no 1Password (vault "MGS Conteúdo"):

| Site | Item 1Password | IP |
|---|---|---|
| finanzas.openzed.com | `openzed finanzas wordpress zeus` | 3.19.138.131 |
| finanzas.cliquet.com | `cliquet finanzas wordpress zeus` | 18.116.18.34 |
| openzed.com | `openzed wordpress zeus` | 44.208.155.39 |
| cliquet.com | `cliquet wordpress zeus` | 35.175.97.196 |

SFTP items (para validação final):

| Site | Item 1Password | Campo senha |
|---|---|---|
| finanzas.openzed.com | `SFTP finanzas.openzed servers` | `wpfiles` |
| finanzas.cliquet.com | `SFTP finanzas.cliquet servers` | `wpfiles` |
| openzed.com | `SFTP openzed servers` | `wpfiles` |
| cliquet.com | `SFTP cliquet servers` | `wpfiles` |

### CRÍTICO — dois conjuntos de credenciais por item WP

Cada item WP tem campos distintos para usos distintos:

| Contexto | Campo 1Password | Uso |
|---|---|---|
| Login browser (File Manager UI) | `username` + `password` | Passo 3 — autenticação wp-admin |
| REST API | `api_auth_user` + `api_application_password` | curl, validação, install/remove plugins |

**Nunca confundir.** Usar o campo errado → 401 constante.

```bash
# Browser login
WP_USER=$(op item get "openzed finanzas wordpress zeus" --vault "MGS Conteúdo" --fields label=username --reveal)
WP_PASS=$(op item get "openzed finanzas wordpress zeus" --vault "MGS Conteúdo" --fields label=password --reveal)

# REST API
AUTH_USER=$(op item get "openzed finanzas wordpress zeus" --vault "MGS Conteúdo" --fields label=api_auth_user --reveal)
APP_PASS=$(op item get "openzed finanzas wordpress zeus" --vault "MGS Conteúdo" --fields label=api_application_password --reveal)
API="https://finanzas.openzed.com/wp-json/wp/v2"
```

---

## Fluxo completo — site que JÁ TEM mu-plugins (ex: canário)

Usado em finanzas.openzed.com onde mu-plugins existia mas yoast-rest-meta.php estava corrompido.

### Passo 1 — Gerar base64 do arquivo correto
```bash
base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php
# Verificar que só tem alphanum + /+= (zero backslashes)
```

### Passo 2 — Login browser + abrir File Manager
```
browser_navigate → https://SITE/rodloguda
→ preencher username + password (campo password, não api_application_password)
→ aguardar wp-admin dashboard
→ browser_navigate → wp-admin/admin.php?page=wp_file_manager
→ aguardar elFinder inicializar
```

### Passo 3a — Capturar hash real do arquivo (SEMPRE fazer, mesmo com hash "conhecido")
```javascript
var ef = jQuery('#wp_file_manager').elfinder('instance');
ef.request({
  data: { cmd: 'ls', target: 'l1_d3AtY29udGVudC9tdS1wbHVnaW5z', intersect: [] }
}).done(function(d) {
  window._hashes = d;
  console.log('Hashes:', JSON.stringify(d));
});
// Inspecionar _hashes para confirmar hash do arquivo alvo
```

**Hashes elFinder conhecidos (base64 de paths — estáveis entre sessões):**
- `wp-content/` → `l1_d3AtY29udGVudA`
- `wp-content/mu-plugins/` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5z`
- `hide-from-home.php` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5zL2hpZGUtZnJvbS1ob21lLnBocA`
- `yoast-rest-meta.php` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5zL3lvYXN0LXJlc3QtbWV0YS5waHA`

### Passo 3b — Backup do conteúdo atual (antes de sobrescrever)
```javascript
ef.request({
  data: { cmd: 'get', target: window._yoast_hash }
}).done(function(d) {
  window._backup_yoast_rest_meta = d.content;
  console.log('Backup OK, len=' + (d.content ? d.content.length : 0));
});
```

### Passo 3c — Sobrescrever via base64 + error handling
```javascript
var b64 = 'BASE64_AQUI'; // output do passo 1
ef.request({
  data: {
    cmd: 'put',
    target: window._yoast_hash, // hash capturado no 3a
    content: atob(b64),
    encoding: ''
  },
  notify: { type: 'save', cnt: 1 }
})
.done(function(d) {
  window._fix = d;
  window._fix_ok = !(d && d.error);
  console.log('Result:', window._fix_ok ? 'SUCCESS' : 'ERROR', JSON.stringify(d));
})
.fail(function(x, t) {
  window._fix_ok = false;
  window._fix_error = { status: x.status, text: t };
  console.log('FAIL:', x.status, t);
});
// Verificar window._fix_ok === true antes de prosseguir
```

---

## Fluxo WPCode snippet — passos OBRIGATÓRIOS (incluindo cleanup)

Ao usar o método WPCode snippet (ver política de escolha acima), os passos são **numerados e obrigatórios** — não narrativos. Não avançar para o próximo passo sem concluir o atual.

```
Passo 1 — Gerar b64 + validar MD5 reverso (NUNCA inventar)
Passo 2 — Copiar template canônico (templates/wpcode-snippet-template.php) e substituir ${B64_PAYLOAD}
Passo 3 — Login browser + criar snippet no WPCode com o PHP do template
Passo 4 — Navegar para wp-admin/index.php (dispara admin_init → executa o snippet)
Passo 5 — Validar MD5 do arquivo em disco via SFTP get + md5sum (069270de4c07a9d15838ff45df65f539)
Passo 6 — REMOVER SNIPPET (detalhes em ### PASSO 6 abaixo — OBRIGATÓRIO)
Passo 7 — Validar REST API (post de teste com _hide_from_home + _yoast_wpseo_title)
Passo 8 — Desativar + remover WP File Manager via REST API
```

### PASSO 6 — REMOVER SNIPPET (OBRIGATÓRIO — não-negociável)

Após validar deploy via MD5 (Passo 5), executar os seguintes sub-passos antes de qualquer outra ação:

1. Login wp-admin do site (mesma sessão se ainda válida)
2. Navegar: **Code Snippets** (WPCode) → listar snippets ativos
3. Localizar o snippet `zeus-deploy-v4-once` (ou nome exato usado no deploy)
4. **DELETAR PERMANENTEMENTE** (duas etapas obrigatórias):
   - Clicar nos 3 pontos → "Move to Trash"
   - Navegar para a aba Trash → "Delete Permanently"
5. **Validar via método NÃO-CIRCULAR** (não usar `/wp-json` — REST API pode estar indisponível se snippet teve parse error):
   - Recarregar a página Code Snippets
   - Confirmar visualmente que snippet **não aparece** nem em Active nem em Trash
   - Opcional (se plugin de query disponível): `SELECT COUNT(*) FROM wp_posts WHERE post_type='wpcode' AND post_title LIKE 'zeus-deploy%'` → deve retornar 0
6. Só após confirmação visual: prosseguir para Passo 7

**Falha em qualquer sub-step = deploy NÃO está completo.** Reportar como pendente e tentar cleanup novamente antes de declarar conclusão.

### FASES FORMAIS DO DEPLOY

Deploy NÃO termina quando o arquivo é escrito em disco. São **duas fases distintas**:

#### FASE 1 — Deploy Completo
**Critério:** arquivo escrito em disco + MD5 validado (Passo 5) + snippet REMOVIDO (Passo 6)  
**Saída:** site tem mu-plugin v4 em disco e nenhum artefato temporário no banco.

#### FASE 2 — Deploy Validado
**Critério:** REST API confirma campos Yoast E `_hide_from_home` funcionando (Passo 7) + frontend HTTP 200 + wp-admin acessível  
**Saída:** confirmação empírica de que o mu-plugin está executando corretamente em runtime.

**Site só é marcado como ✅ no relatório APÓS ambas as fases concluídas.** Marcar ✅ apenas com Fase 1 = relatório incompleto.

### EXIT CHECKLIST (obrigatório antes de declarar site ✅)

Antes de marcar deploy como concluído, todos os checks abaixo devem estar confirmados:

```
[ ] MD5 do arquivo em /wp-content/mu-plugins/yoast-rest-meta.php = 069270de4c07a9d15838ff45df65f539
[ ] hide-from-home.php DELETADO de /wp-content/mu-plugins/ (confirmado via SFTP ls)
[ ] Snippet zeus-deploy-v4-once REMOVIDO permanentemente (verificado visualmente em Code Snippets — NEM em Active NEM em Trash)
[ ] WP File Manager DESATIVADO E DELETADO (GET /wp/v2/plugins não lista wp-file-manager)
[ ] update_option zeus_deploy_v4_status existe em wp_options (evidência de auditoria)
[ ] Site responde HTTP 200 no frontend: curl -I https://SITE
[ ] wp-admin acessa normalmente (login funcional)
[ ] REST API responde wp/v2 (validação adicional após cleanup)
```

**Sem TODOS os checks marcados, deploy NÃO está completo.**

> **Causa histórica desta regra:** Post-mortem 2026-04-26 revelou que em 2 de 3 deploys via WPCode snippet (finanzas.openzed.com sessão 03:00, finanzas.cliquet.com sessão 07:14), o snippet foi esquecido no banco. Rodolfo detectou na auditoria manual e deletou manualmente. A 3ª sessão (cliquet.com 08:00) limpou apenas por estar imediatamente após o incidente openzed — cleanup dependia de memória de sessão, não de procedimento. Esta seção corrige esse gap estrutural.

---

## Fluxo completo — site NOVO sem mu-plugins

Usado em finanzas.cliquet.com, openzed.com, cliquet.com.

### Passo A — Instalar WP File Manager via REST API (instala + ativa em 1 call)
```bash
curl -s -u "$AUTH_USER:$APP_PASS" -X POST \
  "$API/plugins" \
  -H "Content-Type: application/json" \
  -d '{"slug":"wp-file-manager","status":"active"}'
# Esperar: "status":"active", "plugin":"wp-file-manager/file_folder_manager"
```

**Se retornar `folder_exists` (500):** O plugin já estava instalado mas inativo. Apenas ativar:
```bash
curl -s -u "$AUTH_USER:$APP_PASS" -X POST \
  "$API/plugins/wp-file-manager/file_folder_manager" \
  -H "Content-Type: application/json" \
  -d '{"status":"active"}'
```

### Passo B — Login browser + abrir File Manager
```
browser_navigate → https://SITE/rodloguda
→ credenciais browser (username + password)
→ browser_navigate → wp-admin/admin.php?page=wp_file_manager
```

### Passos C+D+E — MEGA-SCRIPT: mkdir + 2 uploads em uma única browser_console call

**Economia: de ~10 roundtrips para 1.** Usar Promise chain — mkdir → upload hide → upload yoast em sequência encadeada.

```javascript
(function() {
  var B64_HIDE  = 'BASE64_HIDE_FROM_HOME'; // base64 -w 0 hide-from-home.php
  var B64_YOAST = 'BASE64_YOAST';          // base64 -w 0 yoast-rest-meta.php

  var ef = jQuery('#wp_file_manager').elfinder('instance');
  if (!ef) { window._deploy = {error:'elfinder not ready'}; return 'NOT READY'; }
  var WC = 'l1_d3AtY29udGVudA';      // hash de wp-content/ (estável)
  var MU = 'l1_d3AtY29udGVudC9tdS1wbHVnaW5z'; // hash de mu-plugins/ (estável)
  window._deploy = { steps: [] };

  function mkfileAndPut(name, b64) {
    return ef.request({ data: { cmd: 'mkfile', target: MU, name: name } })
      .then(function(d) {
        return ef.request({ data: { cmd: 'put', target: d.added[0].hash, content: atob(b64), encoding: '' } });
      })
      .then(function(r) {
        window._deploy.steps.push({ file: name, ok: !(r&&r.error), size: r.changed?r.changed[0].size:null });
      });
  }

  // mkdir (tolera falha se pasta já existe) → upload hide → upload yoast
  ef.request({ data: { cmd: 'mkdir', target: WC, name: 'mu-plugins' } })
    .then(function(d) {
      window._deploy.steps.push({ mkdir: 'ok' });
      return mkfileAndPut('hide-from-home.php', B64_HIDE);
    }, function() {
      window._deploy.steps.push({ mkdir: 'skipped-exists' });
      return mkfileAndPut('hide-from-home.php', B64_HIDE);
    })
    .then(function() { return mkfileAndPut('yoast-rest-meta.php', B64_YOAST); })
    .done(function() { window._deploy.done = true; console.log('DONE:', JSON.stringify(window._deploy)); })
    .fail(function(x,t) { window._deploy.error = {s:x?x.status:'?',t:t}; console.log('FAIL:', JSON.stringify(window._deploy)); });

  return 'deploy running';
})()
```

Verificar `window._deploy.done === true` e todos os `steps[].ok === true` antes de prosseguir.

**Nota:** Se os arquivos já existirem (`errExists`), o `mkfile` falhará. Nesse caso usar `cmd: put` direto com o hash conhecido (ver Passo 3c do fluxo de canário).

---

## Validação REST API (igual para todos os sites)

**IMPORTANTE:** `register_rest_field` (Yoast) expõe campos no **nível raiz** do objeto post, não dentro de `meta`. `register_post_meta` (_hide_from_home) fica dentro de `meta`.

```bash
# Criar post de teste
POST_ID=$(curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/posts" \
  -H "Content-Type: application/json" \
  -d '{"status":"draft","title":"_zeus_test","meta":{"_hide_from_home":"1"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# PATCH com campos Yoast no nível raiz
curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d '{"_yoast_wpseo_title":"zeus_test_title","_yoast_wpseo_metadesc":"zeus_test_desc","_yoast_wpseo_focuskw":"zeus_kw"}'

# Ler e verificar
curl -s -u "$AUTH_USER:$APP_PASS" "$API/posts/$POST_ID?context=edit" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('_hide_from_home:', d.get('meta',{}).get('_hide_from_home'))   # deve ser '1'
print('_yoast_wpseo_title:', d.get('_yoast_wpseo_title'))             # deve ser 'zeus_test_title'
print('_yoast_wpseo_metadesc:', d.get('_yoast_wpseo_metadesc'))       # deve ser 'zeus_test_desc'
"

# Limpar
curl -s -u "$AUTH_USER:$APP_PASS" -X DELETE "$API/posts/$POST_ID?force=true" > /dev/null
```

Esperado:
- `_hide_from_home`: `'1'` (string, não boolean `true`)
- `_yoast_wpseo_title`: `'zeus_test_title'`

Se `_hide_from_home` retornar `null` ao enviar `true` (boolean), usar `"1"` (string).

---

## Remover WP File Manager (pós-validação)

**ATENÇÃO:** O endpoint DELETE exige desativação prévia. Não é possível deletar plugin ativo diretamente.

```bash
# 1. Listar plugins para confirmar slug exato
curl -s -u "$AUTH_USER:$APP_PASS" "$API/plugins?status=active" \
  | python3 -c "import sys,json; [print(p['plugin']) for p in json.load(sys.stdin)]"
# Slug esperado: wp-file-manager/file_folder_manager

# 2. Desativar
curl -s -u "$AUTH_USER:$APP_PASS" -X POST \
  "$API/plugins/wp-file-manager/file_folder_manager" \
  -H "Content-Type: application/json" \
  -d '{"status":"inactive"}'

# 3. Deletar (agora funciona)
curl -s -u "$AUTH_USER:$APP_PASS" -X DELETE \
  "$API/plugins/wp-file-manager/file_folder_manager?force=true"
# Esperar: "deleted": true
```

**Nota:** URL do endpoint usa `/` (não `%2F`) — testado e confirmado. O `%2F` resulta em 404.

---

## Validação SFTP pós-deploy

```bash
SFTP_PASS=$(op item get "SFTP finanzas.openzed servers" --vault "MGS Conteúdo" --fields label=wpfiles --reveal)

sshpass -p "$SFTP_PASS" sftp -o StrictHostKeyChecking=no -P 22 wpfiles@3.19.138.131 <<'EOF'
ls -la wp-content/mu-plugins/
EOF
# Esperar: hide-from-home.php (1352 bytes) + yoast-rest-meta.php (3483 bytes)
```

---

## Política de canário (obrigatório)

Sempre sequencial, aguardar aprovação entre cada site:
1. `finanzas.openzed.com` — canário, menor impacto
2. `finanzas.cliquet.com`
3. `openzed.com`
4. `cliquet.com`

---

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

---

## Método alternativo — WPCode PHP Snippet (quando WP File Manager não está disponível)

**Testado em 2026-04-25 em finanzas.openzed.com e finanzas.cliquet.com.**

O WPCode (plugin "insert-headers-and-footers") está instalado em todos os 4 sites SFTP MGS. Permite criar snippets PHP ativos que rodam em `admin_init`.

### Fluxo

1. **Login browser** no WP Admin
2. **Navegar** para `wp-admin/admin.php?page=wpcode-snippet-manager&custom=1`
3. **Preparar PHP do snippet a partir do template canônico** (NUNCA regenerar inline):

```bash
# 1. Ler o template canônico
cat /root/.hermes/profiles/zeus/skills/ops/wp-rest-mu-plugin-deploy/templates/wpcode-snippet-template.php

# 2. Gerar b64 fresco
b64=$(base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php)

# 3. Validar MD5 reverso (OBRIGATÓRIO — não pular)
echo "$b64" | base64 -d | md5sum
# Deve retornar: 069270de4c07a9d15838ff45df65f539 — se divergir: NÃO PROSSEGUIR

# 4. Substituir ${B64_PAYLOAD} no template pelo $b64 validado
# Resultado = phpCode pronto para injetar no CodeMirror

# 5. NÃO reescrever o PHP manualmente — sempre copiar literal do template substituído
```

**Via console JS no WPCode (`page=wpcode-snippet-manager&custom=1`):**

```javascript
// phpCode = conteúdo do template canônico com ${B64_PAYLOAD} substituído pelo b64 validado
// NUNCA escrever este PHP manualmente ou regenerar inline — causa variações entre sessões
var phpCode = `COLAR_AQUI_TEMPLATE_COM_B64_SUBSTITUIDO`;

var typeSelect = document.querySelector('select[name="wpcode_snippet_type"]');
typeSelect.value = 'php';
typeSelect.dispatchEvent(new Event('change', {bubbles: true}));

var cm = document.querySelector('.CodeMirror')?.CodeMirror;
if (cm) cm.setValue(phpCode);

// ⚠️ #wpcode_snippet_title pode não existir — usar seletor por name que é mais confiável
var titleField = document.querySelector('input[name="wpcode_snippet_title"]') || document.querySelector('#wpcode_snippet_title');
if (titleField) { titleField.value = 'zeus-deploy-v4-once'; titleField.dispatchEvent(new Event('input', {bubbles: true})); titleField.dispatchEvent(new Event('change', {bubbles: true})); }
var checkbox = document.querySelector('#wpcode_active');
if (checkbox && !checkbox.checked) checkbox.click();

// Usar match exato — "Save to Library" é botão diferente, não usar includes('Save')
var saveBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
  var t = b.textContent.trim();
  return t === 'Save Snippet' || t === 'Guardar Snippet' || t.includes('Guardar');
});
if (saveBtn) saveBtn.click();
({type: typeSelect.value, codeLen: cm?.getValue()?.length, active: checkbox?.checked})
```

4. **Navegar** para `wp-admin/index.php` — dispara `admin_init`, snippet executa
5. **Validar** via SFTP: baixar o arquivo e verificar MD5

### ⚠️ AVISOS CRÍTICOS do método WPCode snippet

> **Ver "POLÍTICA DE ESCOLHA DE MÉTODO" no topo da skill antes de usar este método.**
> WPCode snippet é método de alto risco em Bitnami sem .pem — elFinder é sempre preferível.

- **NUNCA** montar o b64 manualmente ou copiar de outra call. Sempre gerar com `base64 -w 0 /caminho/arquivo.php` em tempo real antes da injeção.
- **NUNCA** editar a string b64 depois de gerada — qualquer caractere extra ou typo cria arquivo PHP inválido.
- **SEMPRE** fazer validação MD5 reversa antes de ativar (ver seção "Validação MD5 reversa" no topo).
- Um snippet PHP com parse error causa **PHP fatal error** → **site 100% down** (HTTP 500, frontend + admin + REST API). WPCode Safe Mode não consegue interceptar parse errors (ocorrem antes dos hooks do WP). **Em Bitnami sem .pem, isso é irrecuperável sem AWS Console.**
- Verificar MD5 do arquivo após deploy via SFTP `get` + `md5sum` — não confiar no "admin carregou OK" como validação suficiente.
- Após confirmar deploy via MD5, deletar o snippet temporário pelo WP Admin antes de sair.
- **Incidente documentado:** 2026-04-25 openzed.com ficou DOWN por b64 corrompido em snippet WPCode. Recuperação dependeu de dev externo + AWS Console. Ver CASE STUDY L2 no SOUL.md do Zeus.

### Recuperação de site down por snippet com parse error

Se um snippet PHP com erro foi salvo ativo e o site está HTTP 500:

1. **Tentar WPCode Safe Mode:** `https://SITE/rodloguda?wpcode-safe-mode=1`
   - Funciona APENAS se o parse error estiver em snippet carregado via `eval()` (late-binding)
   - NÃO funciona se WPCode inclui o snippet como arquivo (ocorre antes dos filtros do WP)

2. **Se Safe Mode falhar — opções sem SSH:**
   - `wpfiles` SFTP é read-only — impossível remover via SFTP
   - REST API estará HTTP 500 — impossível usar

3. **Única solução sem chave bitnami:** Acesso MySQL direto
   ```sql
   UPDATE wp_posts SET post_status = 'draft'
   WHERE post_type = 'wpcode' AND post_title = 'zeus-deploy-v4-once';
   ```
   Ou acessar via AWS Console (Lightsail/EC2) → SSH como `bitnami` → `mysql -u root`

4. **Se tiver chave .pem bitnami:**
   ```bash
   ssh -i /caminho/chave.pem bitnami@IP
   mysql -u root wordpress -e "UPDATE wp_posts SET post_status='draft' WHERE post_type='wpcode' AND post_title LIKE 'zeus-deploy%';"
   sudo /opt/bitnami/ctlscript.sh restart apache
   ```

---

## Pitfalls críticos

1. **PITFALL PRINCIPAL — Backslash duplicado no elFinder:** Nunca passar conteúdo PHP com backslashes diretamente como string JavaScript. O browser interpreta `\` como escape character, duplicando-os no arquivo final. **Sempre usar base64:** `atob('BASE64')` decodifica sem perda de backslashes.

2. **Login WP via browser com cookies bloqueados:** Se aparecer erro "las cookies están bloqueadas", executar `document.cookie = "test=1; path=/"` no console antes de submeter o form. O Playwright bloqueia cookies em algumas configurações.

3. **Campos Yoast no nível raiz vs meta:** `register_rest_field` expõe campos diretamente no objeto post root. Enviar dentro de `meta` no POST de criação não funciona — usar PATCH separado com campos no nível raiz.

4. **_hide_from_home como string:** O mu-plugin registra como `type: string`. Enviar `true` (boolean JSON) pode retornar `null`. Usar `"1"` (string).

5. **DELETE plugin exige desativação prévia:** `DELETE /wp/v2/plugins/...` retorna 400 `rest_cannot_delete_active_plugin` se ativo. Sempre desativar primeiro com POST `{"status":"inactive"}`.

6. **URL do endpoint de plugin com slash, não %2F:** `wp-file-manager/file_folder_manager` funciona. `wp-file-manager%2Ffile_folder_manager` retorna 404.

7. **Hash elFinder:** É base64 do path relativo, prefixado com `l1_`. Estável entre sessões e reinstalações do File Manager. O hash de `wp-content/mu-plugins/` é sempre `l1_d3AtY29udGVudC9tdS1wbHVnaW5z` nestes servidores Bitnami. Validar antes de usar via `cmd: ls`.

8. **SFTP user é `wpfiles`, senha no campo `wpfiles` do item "SFTP ... servers"** — não confundir com `username` do item WP.

9. **b64 corrompido em snippets WPCode:** Ao injetar b64 via console JS, qualquer edição ou cópia parcial da string gera PHP inválido → site down. SEMPRE gerar b64 fresco com `base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php` imediatamente antes de usar, e copiar o output completo sem modificação.

10. **WPCode = insert-headers-and-footers:** O plugin "WPCode Lite" está instalado nesses sites com o slug `insert-headers-and-footers` (nome histórico). `wp-json/wp/v2/plugins/wpcode-lite/...` não funciona — usar `insert-headers-and-footers/ihaf`.

11. **"Save Snippet" ≠ "Save to Library":** A página de criação tem dois botões distintos. `Save to Library` (id=`wpcode_save_to_library`) salva para a biblioteca cloud WPCode — não é isso. O correto é `Save Snippet` (sem id, texto exato). Usar match de texto exato, não `includes('Save')` — senão pode clicar no botão errado.

12. **Remover snippet via URL direta com nonce:** Após execução, pegar o nonce do link Trash na listagem (`page=wpcode`) e navegar direto para `wp-admin/admin.php?page=wpcode&action=trash&snippet_id=XXXX&_wpnonce=YYYY`. Mais confiável que clicar em elementos dinâmicos. Confirmar via `document.querySelectorAll('tr')` — snippet some da lista + notice "moved to Trash".

13. **Menu "Code Snippets" = WPCode:** No admin sidebar, WPCode aparece como "Code Snippets". URLs: listagem = `admin.php?page=wpcode`, novo snippet = `admin.php?page=wpcode-snippet-manager&custom=1`.

14. **mu-plugin PHP corrompido em disco = 500 mesmo após remover snippet WPCode:** Se o snippet WPCode escreveu um arquivo PHP inválido em `mu-plugins/`, remover o snippet não resolve — o arquivo continua em disco, sendo carregado automaticamente pelo WP no boot. O 500 persiste. Solução: substituir o arquivo em disco pelo canonical correto. Verificar via SFTP `get` + `md5sum` para confirmar que o arquivo no servidor é realmente o canonical.

15. **Dev externo "recuperando" site pode não corrigir o conteúdo:** Ao receber site de volta após recuperação por terceiros, SEMPRE verificar MD5 do arquivo em disco via SFTP antes de assumir que está ok. Dev externo pode ter feito apenas backup/rename sem corrigir o PHP inválido — o mesmo conteúdo corrompido pode estar em `.bak`, `.disabled` e no arquivo ativo ao mesmo tempo (todos com o mesmo MD5 corrompido). Confirmado em openzed.com 2026-04-25.

16. **Cloudflare cache mascara PHP 500:** Site Bitnami com PHP fatal error pode responder HTTP 200 no frontend se Cloudflare estiver servindo cache — dá falsa sensação de "site funcionando". Sempre testar endpoint autenticado (ex: `GET /wp-json/wp/v2/users/me`) para confirmar que PHP está executando corretamente, não apenas o cache edge.
