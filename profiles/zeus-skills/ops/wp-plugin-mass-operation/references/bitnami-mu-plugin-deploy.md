# Bitnami/AWS — Deploy de mu-plugins via elFinder + WPCode

Conteúdo originalmente em skill `wp-rest-mu-plugin-deploy` (arquivada 2026-05-06).

## PITFALL FATAL — NUNCA inventar b64

Antes de qualquer deploy que envolva b64 de arquivo PHP:

```bash
# 1. GERAR — sempre via shell, nunca manualmente
b64=$(base64 -w 0 /caminho/arquivo.php)

# 2. VALIDAR reverso — MD5 deve bater com o original
[ "$(echo "$b64" | base64 -d | md5sum | awk '{print $1}')" = \
  "$(md5sum /caminho/arquivo.php | awk '{print $1}')" ] && echo "OK" || echo "FALHOU — NÃO PROSSEGUIR"
```

> **Caso histórico:** openzed.com 2026-04-25 — Zeus inventou b64 manualmente → PHP `'key'2` na linha 79 → site DOWN 18+ horas.

---

## Política de escolha de método

| Método | Risco | Quando usar |
|---|---|---|
| **elFinder `cmd: put`** | ✅ Baixo | Sempre preferido. Escreve em disco, não executa PHP na escrita. |
| **WPCode snippet** | ❌ Alto | Última opção. Parse error = site DOWN irrecuperável sem .pem. |

**Regra absoluta:** Nunca usar WPCode snippet em Bitnami sem .pem disponível para recuperação.

---

## Credenciais dos 4 sites Bitnami

Items canônicos no 1Password (vault "MGS Conteúdo"):

| Site | Item 1Password | IP |
|---|---|---|
| finanzas.openzed.com | `Wordpress - finanzas.openzed.com` | 3.19.138.131 |
| finanzas.cliquet.com | `Wordpress - finanzas.cliquet.com` | 18.116.18.34 |
| openzed.com | `Wordpress - openzed.com` | 44.208.155.39 |
| cliquet.com | `Wordpress - cliquet.com` | 35.175.97.196 |

Se houver título duplicado, selecione o UUID que contenha os campos esperados e valide-o por smoke REST autenticado (`/wp-json/wp/v2/users/me?context=edit` HTTP 200, role administrator) antes de qualquer write. Nunca escolha só pelo título.

### Dois conjuntos de credenciais por item (CRÍTICO)

| Contexto | Campo 1Password | Uso |
|---|---|---|
| Login browser (File Manager UI) | `username` + `password` | Autenticação wp-admin |
| REST API (padrão) | `api_auth_user` + `api_application_password` | curl, validação, install/remove plugins |
| REST API (`cliquet.com`) | `username` + `wp_app_password` | Exceção de campos validada por smoke autenticado |

---

## Fluxo elFinder — site com mu-plugins existente

### Passo 1 — Gerar base64
```bash
base64 -w 0 /root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php
# MD5 canônico: 069270de4c07a9d15838ff45df65f539
```

### Passo 2 — Login + abrir File Manager
```
browser_navigate → https://SITE/rodloguda → username + password
browser_navigate → wp-admin/admin.php?page=wp_file_manager
```

### Passo 3a — Capturar hash real do arquivo
```javascript
var ef = jQuery('#wp_file_manager').elfinder('instance');
ef.request({
  data: { cmd: 'ls', target: 'l1_d3AtY29udGVudC9tdS1wbHVnaW5z', intersect: [] }
}).done(function(d) { window._hashes = d; console.log('Hashes:', JSON.stringify(d)); });
```

**Hashes elFinder conhecidos (estáveis entre sessões):**
- `wp-content/` → `l1_d3AtY29udGVudA`
- `wp-content/mu-plugins/` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5z`
- `hide-from-home.php` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5zL2hpZGUtZnJvbS1ob21lLnBocA`
- `yoast-rest-meta.php` → `l1_d3AtY29udGVudC9tdS1wbHVnaW5zL3lvYXN0LXJlc3QtbWV0YS5waHA`

### Passo 3c — Sobrescrever via base64
```javascript
var b64 = 'BASE64_AQUI';
ef.request({
  data: { cmd: 'put', target: window._yoast_hash, content: atob(b64), encoding: '' },
  notify: { type: 'save', cnt: 1 }
}).done(function(d) { window._fix_ok = !(d && d.error); console.log('Result:', window._fix_ok, JSON.stringify(d)); });
// Verificar window._fix_ok === true antes de prosseguir
```

---

## Fluxo elFinder — site NOVO sem mu-plugins

### MEGA-SCRIPT: mkdir + 2 uploads em uma call

```javascript
(function() {
  var B64_HIDE  = 'BASE64_HIDE_FROM_HOME';
  var B64_YOAST = 'BASE64_YOAST';
  var ef = jQuery('#wp_file_manager').elfinder('instance');
  if (!ef) { window._deploy = {error:'elfinder not ready'}; return 'NOT READY'; }
  var WC = 'l1_d3AtY29udGVudA';
  var MU = 'l1_d3AtY29udGVudC9tdS1wbHVnaW5z';
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

---

## Instalar WP File Manager via REST API
```bash
AUTH_USER=$(op item get "ITEM" --vault "MGS Conteúdo" --fields label=api_auth_user --reveal)
APP_PASS=$(op item get "ITEM" --vault "MGS Conteúdo" --fields label=api_application_password --reveal)
API="https://SITE/wp-json/wp/v2"

curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/plugins" \
  -H "Content-Type: application/json" \
  -d '{"slug":"wp-file-manager","status":"active"}'
```

## Remover WP File Manager pós-deploy

### Regra operacional — plugin temporário, não permanente

WP File Manager (`wp-file-manager/file_folder_manager`) é uma ferramenta temporária de deploy para sites Bitnami/AWS sem SSH de escrita. Se for instalado/ativado para elFinder, ele deve ser desativado e deletado no mesmo fluxo, depois de validar MD5/REST/API do deploy.

Se Rodolfo perguntar depois “quem instalou o File Manager?”, não responder de memória e não assumir que a pergunta é sobre a última publicação/REC. Auditar sessões/logs/docs/filesystem e responder a pergunta de proveniência diretamente. Ver também `references/wp-file-manager-provenance-audit.md`.

Padrões históricos úteis:
- `session_20260425_031415_6d7b13` mostra Zeus instalando WP File Manager via REST em pelo menos `finanzas.cliquet.com` durante Fase 2.5.
- `openzed.com` teve uso manual pelo Rodolfo para recovery; Zeus registrou remoção em 2026-04-26 (`commit 5a0476a`).
- Presença atual do plugin em site MGS deve ser tratada como resíduo de deploy até prova contrária; validar e remover, não normalizar como plugin permanente.

```bash
# 1. Desativar
curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/plugins/wp-file-manager/file_folder_manager" \
  -H "Content-Type: application/json" -d '{"status":"inactive"}'
# 2. Deletar
curl -s -u "$AUTH_USER:$APP_PASS" -X DELETE "$API/plugins/wp-file-manager/file_folder_manager?force=true"
```

---

## Validação REST API (pós-deploy)

```bash
POST_ID=$(curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/posts" \
  -H "Content-Type: application/json" \
  -d '{"status":"draft","title":"_zeus_test","meta":{"_hide_from_home":"1"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# PATCH campos Yoast no nível raiz (não dentro de meta)
curl -s -u "$AUTH_USER:$APP_PASS" -X POST "$API/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d '{"_yoast_wpseo_title":"zeus_test_title","_yoast_wpseo_metadesc":"zeus_test_desc"}'

# Verificar
curl -s -u "$AUTH_USER:$APP_PASS" "$API/posts/$POST_ID?context=edit" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('_hide_from_home:', d.get('meta',{}).get('_hide_from_home'))
print('_yoast_wpseo_title:', d.get('_yoast_wpseo_title'))
"
# Limpar
curl -s -u "$AUTH_USER:$APP_PASS" -X DELETE "$API/posts/$POST_ID?force=true" > /dev/null
```

---

## EXIT CHECKLIST (obrigatório antes de marcar site ✅)

```
[ ] MD5 do arquivo yoast-rest-meta.php = 069270de4c07a9d15838ff45df65f539
[ ] Snippet WPCode (se usado) REMOVIDO permanentemente (nem em Active nem em Trash)
[ ] WP File Manager DESATIVADO E DELETADO
[ ] Site responde HTTP 200: curl -I https://SITE
[ ] REST API responde _hide_from_home e _yoast_wpseo_title corretamente
```

---

## Método WPCode snippet — ALTO RISCO (ler política antes de usar)

**Template canônico:** `/root/.hermes/profiles/zeus/skills/ops/wp-plugin-mass-operation/references/wpcode-snippet-template.php`
(Nunca reescrever inline — usar o template, substituindo apenas `${B64_PAYLOAD}`)

### Passo obrigatório após deploy via WPCode
1. Login wp-admin → Code Snippets → localizar `zeus-deploy-v4-once`
2. Move to Trash → Delete Permanently
3. Confirmar visualmente (não aparece em Active nem Trash)

### Recuperação de site DOWN por snippet com parse error
```sql
-- Via MySQL (AWS Console ou bitnami SSH):
UPDATE wp_posts SET post_status = 'draft'
WHERE post_type = 'wpcode' AND post_title = 'zeus-deploy-v4-once';
```

---

## Pitfalls críticos

1. **Backslash duplicado no elFinder** — nunca passar PHP com backslashes como string JS; usar `atob('BASE64')`.
2. **Campos Yoast no nível raiz** — `register_rest_field` expõe no root do objeto, não em `meta`.
3. **`_hide_from_home` como string** — usar `"1"` (string), não `true` (boolean).
4. **DELETE plugin exige desativação prévia** — POST `{"status":"inactive"}` antes.
5. **URL do endpoint de plugin com `/` não `%2F`** — `%2F` retorna 404.
6. **SFTP path relativo** — `get wp-content/mu-plugins/arquivo.php` (sem `/` inicial).
7. **Sessão WP expira em ~5min** — ter b64 pronto ANTES de entrar no admin.
8. **Cloudflare cache mascara HTTP 500** — sempre testar endpoint autenticado para confirmar PHP rodando.
9. **cliquet.com senha pode ser `Zeus_Deploy_2024!`** — foi alterada emergencialmente em 2026-04-23; verificar qual funciona.

## Política de canário (obrigatório)

Sequência: finanzas.openzed.com → finanzas.cliquet.com → openzed.com → cliquet.com
