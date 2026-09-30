# Substituição segura de conteúdo existente no WordPress

Use esta referência para trocar conteúdo demo, texto de tema ou copy institucional em posts, páginas e CPTs já publicados sem perder mídia, estrutura ou indexação.

## 1. Resolva autoridade e gate técnico

1. Valide o domínio no gate MGS.
2. Resolva o `site_key` em `data/sites.json`.
3. Confirme o item dedicado da Atena, publishing user, ID e role sem imprimir segredo.
4. Rode um GET autenticado `context=edit` pelo endpoint real do post type.
5. Se o `site_key` estiver ausente, aplique o fallback pedido. Se Rodolfo superseder o fallback e ordenar conclusão, registre a configuração mínima apenas com campos confirmados e valide o mesmo GET antes de escrever.

Nunca use uma Application Password válida como justificativa para pular `sites.json`.

## 2. Faça snapshot e bloqueio contra estado stale

Para cada ID, salve antes do primeiro write:

- endpoint REST (`posts`, `pages` ou CPT);
- `id`, `slug`, `status`, `type`, `modified`;
- `title.raw`, `content.raw`, `excerpt.raw`;
- `featured_media`, template, taxonomias e meta exposta;
- SHA-256 do `content.raw`;
- IDs e URLs de toda mídia no corpo;
- formulários, CTAs, shortcodes/blocos e links de tracking.

Releia todos os alvos imediatamente antes da primeira escrita e compare `modified` + SHA-256. Pare se qualquer registro mudou; isso evita sobrescrever edição humana ou efeito parcial de outra automação.

## 3. Componha o conteúdo final preservando a estrutura

O draft editorial sem imagens é um fragmento, não o valor final de `content`.

1. Converta parágrafos, headings e listas para blocos Gutenberg válidos.
2. Reutilize os blocos de mídia/shortcodes do raw original, preservando IDs, URLs e ordem.
3. Remova somente texto demo dentro da estrutura preservada: captions falsas, autores fictícios, quotes em pseudo-latim e parágrafos placeholder.
4. Em bloco misto (por exemplo, coluna com imagem + texto demo), mantenha a coluna/imagem e troque apenas o texto.
5. Compare os conjuntos de IDs e URLs de mídia antes/depois; exija igualdade.
6. Exija zero termos demo no payload final exato, não apenas no draft-base.

Preservar mídia não significa preservar caption ou citação fictícia que faz parte do demo.

## 4. Valide capacidades do post type antes de montar metadata

Consulte `OPTIONS /wp-json/wp/v2/<post_type>/<id>` com a identidade editorial.

- Se `schema.properties.meta` existir e os campos Yoast estiverem registrados, envie title/metadesc/focus keyphrase e confira por GET.
- Se `meta` não estiver no schema, não assuma que o PUT falhará: o core pode devolver HTTP 200, ignorar silenciosamente o campo e ainda alterar `modified`.
- Nessa situação, valide a descrição no HTML público. Atualize title/excerpt/content pelos campos suportados e reporte qualquer meta protegida que continue fora do alcance editorial; não alegue que a metadata foi aplicada.

## 5. Escreva um registro por vez com rollback escopado

1. Use `wp_curl_auth_http` e payload explícito com somente os campos autorizados.
2. Omita slug, status, featured media, taxonomias, template e robots quando devem permanecer iguais.
3. Após cada PUT, faça GET autenticado e valide identidade, status, slug, featured media, título, excerpt, hash do raw e meta suportada.
4. Registre o ID como atualizado somente após readback.
5. Se uma etapa posterior falhar, restaure em ordem reversa apenas os registros já atualizados usando o snapshot; depois valide o rollback.

## 6. Faça readback público real

Valide cada URL com cache-buster em desktop e mobile:

- HTTP 200 e canonical original;
- H1/título esperado;
- zero Lorem/pseudo-latim, nomes ou captions demo;
- links internos esperados presentes;
- mesma mídia do corpo e featured image preservada;
- zero imagem quebrada;
- zero overflow horizontal;
- robots efetivos inalterados.

### Lazy loading

Antes de classificar uma imagem como quebrada, force carregamento real: percorra/role a página até o fim, defina `loading=eager` quando necessário, aguarde a rede e só então examine `complete` e `naturalWidth`. Conferir esses campos no topo da página gera falsos positivos em temas que adiam o carregamento.

### Indexação

Use `meta[name="robots"]` no HTML final como evidência efetiva. `yoast_head_json` pode continuar mostrando `index,follow` quando um MU plugin ou tema impõe `noindex,nofollow` no frontend.