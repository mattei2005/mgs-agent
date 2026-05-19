# Post operations - utilities (find by slug, delete with media)

Reference loaded ON DEMAND quando Atena precisa de operacoes auxiliares
em posts ja publicados (achar por slug quando REST falha, deletar post +
media juntos).

Carregada via `view references/post-operations.md` quando necessario.

---

## Finding a post ID when REST API returns empty for a slug

When `GET /wp/v2/posts?slug=<slug>` returns `[]` (even with `status=any` or
`context=edit`), the post may still exist due to plugin interference in
`rest_post_query` filter (Wordfence, Yoast, theme functions, etc).

**Validado em 01/05/2026:** este bug NAO esta ativo no eggbev no momento.
Mas pode voltar se algum plugin atualizar. Mantemos este workaround
documentado por seguranca.

### Workaround: extrair ID do HTML publico

WordPress embeds the post ID in the `<body>` class (e.g. `class="post-62013 ..."`):

```bash
curl -s "https://<domain>/<slug>/" | grep -oE 'post-[0-9]+' | head -1
```

Extract the number: `post-62013` -> ID is `62013`.

Then fetch via `GET /wp/v2/posts/62013?context=edit` to get the full raw content.

### Quando usar

- `check-slug-conflict.sh` retornar `WARN posts_query_zero_results`
- Atena tentar achar post pelo slug e receber `[]` mesmo sabendo que existe
- Antes de criar post novo se houve duvida sobre existencia previa

---

## Post deletion (re-publish flow)

Whenever a post is deleted - **for any reason** (re-publish, slug conflict,
test cleanup, or explicit user request) - **always delete the media
attachments together with the post**, before or at the same time. If the
media files are left orphaned in the library, WordPress auto-renames the
re-uploaded versions with numeric suffixes (`-1`, `-2`, `-3`...), which
breaks the canonical URLs and pollutes the media library.

### Delete order

1. Fetch the post to get `featured_media` ID + parse card media ID from content
2. DELETE `/wp/v2/media/<featured_id>?force=true`
3. DELETE `/wp/v2/media/<card_id>?force=true`
4. DELETE `/wp/v2/posts/<id>?force=true`

```bash
# Example
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/media/61999?force=true"
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/media/62000?force=true"
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/posts/62004?force=true"
```

Confirm each DELETE returns `{"deleted":true}` before re-uploading.

### Quando usar

- Re-publish do mesmo cartao no mesmo site (depois de erro)
- Cleanup de teste
- Pedido explicito do Rodolfo/Raquel para remover post + assets
