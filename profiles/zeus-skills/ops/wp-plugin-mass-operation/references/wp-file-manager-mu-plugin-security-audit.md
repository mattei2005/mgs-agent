# Auditoria de segurança — WP File Manager + mu-plugins

Use quando Rodolfo perguntar se há ação de segurança após uso de `wp-content/mu-plugins`, WP File Manager, elFinder ou WPCode em sites MGS.

## Princípio operacional

`mu-plugins` não é vulnerabilidade por si só; é recurso oficial do WordPress. O risco real é:

- alguém conseguir escrever PHP dentro de `wp-content/mu-plugins/`;
- existir arquivo desconhecido ou divergente do canonical;
- WP File Manager ficar instalado/ativo após alteração;
- snippet WPCode temporário ficar ativo/lixeira após deploy;
- REST/metas expostos sem `current_user_can()`/auth adequada.

Resposta executiva correta: manter mu-plugin necessário, mas auditar superfície de escrita e resíduos temporários.

## Fluxo seguro recomendado

1. Rodar auditoria read-only primeiro. Não remover nem sobrescrever na primeira passada.
2. Inventariar por site:
   - arquivos em `wp-content/mu-plugins/`;
   - MD5 de `yoast-rest-meta.php` contra canonical;
   - presença/status de `wp-file-manager`;
   - presença/status de WPCode/Insert Headers and Footers/Code Snippets;
   - snippets `wpcode` com títulos contendo `zeus`, `deploy`, `mu-plugin`, `yoast`.
   - quando o pedido também incluir plugins customizados, auditar os diretórios exatos em `wp-content/plugins/`: modos de diretórios/arquivos, owner/group, qualquer item gravável por grupo/outros, backups/resíduos dentro do webroot e resposta HTTP externa para a pasta e para extensões de backup conhecidas;
   - revisar o código customizado por credencial embutida, handler público (`wp_ajax_nopriv`/REST), capability + nonce nas mutações administrativas, sanitização, SSRF/URL controlada pelo cliente e rate limiting. Nunca imprimir o valor de uma credencial encontrada; reportar apenas presença, escopo e risco.
3. Interpretar permissões corretamente:
   - diretório `755` não significa “todos podem alterar”: somente o owner escreve; grupo/outros leem e atravessam;
   - arquivo `644` é o padrão comum; somente o owner escreve;
   - `775` permite escrita ao grupo e precisa ser interpretado junto com owner/group e arquitetura do host (por exemplo, Bitnami `daemon`), mas ainda não é world-writable;
   - `777`, bit de escrita para `other`, owner inesperado ou código gravável por um grupo amplo são achados de alto risco;
   - permissão de filesystem não substitui teste HTTP: um diretório pode negar listagem e ainda servir um `.bak` diretamente.
4. Diferenciar achado crítico de diferença de arquitetura:
   - `wp-file-manager` instalado/ativo sem uso atual = resíduo a remover;
   - snippet de deploy órfão = remover após confirmação;
   - mu-plugin desconhecido = parar e reportar antes de remover;
   - ausência de `mu-plugins` em RunCloud não é, sozinha, falha de segurança — pode indicar que o site usa outro mecanismo/pipeline.
5. Confirmar antes de mudar produção.
6. Se autorizado, remover WP File Manager com `plugin deactivate` + `plugin delete` e validar que não está instalado.

## RunCloud — padrão de auditoria read-only

Para sites RunCloud, usar WP-CLI/SSH e coletar TSV compacto:

- `find $WP_PATH/wp-content/mu-plugins -maxdepth 1 -type f -printf '%f,'`
- `md5sum $WP_PATH/wp-content/mu-plugins/yoast-rest-meta.php`
- `wp plugin is-installed wp-file-manager`
- `wp plugin is-active wp-file-manager`
- checar plugins de snippet: `insert-headers-and-footers`, `wpcode`, `code-snippets`
- checar títulos suspeitos:

```sql
SELECT CONCAT(post_status, ':', post_title)
FROM wp_posts
WHERE post_type='wpcode'
  AND (
    LOWER(post_title) LIKE '%zeus%'
    OR LOWER(post_title) LIKE '%deploy%'
    OR LOWER(post_title) LIKE '%mu-plugin%'
    OR LOWER(post_title) LIKE '%yoast%'
  )
ORDER BY ID DESC;
```

Não tratar qualquer WPCode instalado como incidente automaticamente: muitos sites têm snippets editoriais/legados. O foco de segurança são snippets de deploy/Zeus/mu-plugin/Yoast ou código desconhecido.

## Bitnami/AWS — validação possível

Prioridade:

1. REST `/wp-json/wp/v2/plugins` com `api_auth_user` + `api_application_password` para confirmar `wp-file-manager` e plugins de snippet.
2. SFTP `wpfiles` apenas para leitura de arquivos, quando credencial funciona.
3. Se SFTP falhar por credencial stale, reportar como lacuna de auditoria, não como prova de ausência/presença.

Para `cliquet.com`, já houve caso de item 1Password sem `api_application_password`; tratar como lacuna de credencial e não inferir status.

### Fincgriffin — limite do REST para File Manager

No `fincgriffin.com`, a Application Password autenticada pode listar, instalar, ativar, desativar e excluir plugins pelo endpoint REST `/wp-json/wp/v2/plugins`, mas não cria sessão cookie no `wp-admin` nem autentica o `admin-ajax.php`. O conector do `WP File Manager` 8.0.4 exige simultaneamente `current_user_can('manage_options')` e nonce `wp-file-manager`; portanto, instalar o plugin por REST não basta para enumerar arquivos.

Se o login real no WordPress for bloqueado por WAF/2FA (`403`) e não houver SSH/SFTP:

1. não chamar o `admin-ajax` sem capability/nonce nem tentar bypass;
2. desativar e excluir imediatamente qualquer File Manager instalado para o teste, por REST, e validar zero ocorrência;
3. validar home e caminhos públicos, mas não tratar `403` como prova de ausência física;
4. registrar a enumeração interna como lacuna até existir sessão administrativa real ou acesso SSH/SFTP;
5. limpar artefatos locais e não deixar o File Manager instalado apenas para uma tentativa futura.

## Comunicação com Rodolfo

Formato recomendado:

- “Executei auditoria read-only. Não alterei nada.”
- listar apenas achados acionáveis;
- separar lacunas de validação;
- pedir confirmação antes de remover/deletar qualquer plugin em produção.
