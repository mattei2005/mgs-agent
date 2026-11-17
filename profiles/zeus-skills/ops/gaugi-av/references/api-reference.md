# Referência consolidada — Gaudi Public API

## Proveniência e alcance

Fonte: TXT e 23 screenshots de documentação enviados por Rodolfo na thread 1572259906902425653, mais imagem inicial dos títulos das credenciais. Complemento: GETs autenticados de leitura em 2026-11-17. Screenshots e TXT divergem; ver `documentation-conflicts.md`. Exemplos são ilustrativos e não garantem schemas completos. Catálogo real vence exemplos para `blocks_json`.

Base HTTPS: `https://mosaic-api-1453299254.us-east1.run.app`.
Autenticação em cada chamada: Bearer API key Gaudi, criada em Gaudi Studio > Settings > Developers API. Chave exibida em plaintext só na criação; revogação nessa interface. Não criar, revogar ou substituir chave sem confirmação crítica. Tenant inferido da chave; não enviar `tenant_id`. Chaves tenant-scoped alcançam recursos do tenant conforme scopes. Não há introspecção de permissões descrita.

## Convenções

- IDs opacos; não derivar ID de domínio nem trocar prefixos/normalizar valores.
- Timestamps ISO-8601 UTC. Exibir datas ao usuário no timezone pertinente, mantendo original na evidência.
- Cursores opacos; devolver sem alterar junto aos mesmos filtros; quando final nulo, paginação encerrada. Não supor paginação de sites/assets onde contrato não a descreve.
- Campo omitido em update parcial preserva valor; `null` limpa apenas campos que aceitam null. Na criação, omitido usa default. Merge profundo de objetos como social_links não foi documentado.
- Erro: `error` código de máquina, `message` texto, `details` opcional. Exemplos details: `field`, `code`, `message`.
- `blocks_json`: array ordenado de objetos `{id, type, data}` com ID estável. `type` é o `key` do catálogo; `data` obedece ao schema. Não supor suporte a um tipo por aparecer no exemplo.
- `compliance_warnings`: lista de problemas não necessariamente bloqueantes de uma escrita, com `code`, `message`, `field`, `severity`. Exemplo `broken_link`, campo `blocks_json[1].data.html`, severity `warning`. Publicação pode ser bloqueada com 422.

## Scopes distintos documentados

- `read:sites`: descobrir sites, IDs e locales.
- `read:authors`: listar autores.
- `write:authors`: criar, editar, reatribuir artigos e excluir autores.
- `read:categories`: ler metadata de categoria via payload de artigos; nenhum GET standalone documentado.
- `write:categories`: criar, editar metadata e excluir categorias.
- `read:assets`: listar biblioteca de mídia do tenant.
- `write:assets`: upload e exclusão de mídia.
- `read:articles`: listar e ler artigos/traduções.
- `write:articles`: criar, editar, publicar e excluir artigos/traduções.
- `read:blocks`: catálogo e schemas de blocos.
- `read:llm`: documentação machine-readable.

O screenshot repete `read:llm` e em uma linha chama llm.txt de público; outra exige scope/Bearer. O acesso autenticado funciona; acesso anônimo não foi validado. Não inferir scopes de escrita a partir de leituras.

## Sites

### GET /v1/sites — read:sites

Retorna 200 `{sites:[...]}`. Site observado/documentado: `id`, `domain`, `locales`, `default_locale`, `multilingual`, `tagline`. Descobrir IDs antes das operações site-specific. Não há escrita de site documentada.

## Autores — recursos compartilhados entre sites do tenant

### GET /v1/authors — read:authors

Query opcionais: `q` string; `cursor` string; `limit` inteiro 1–100, default 50. Screenshots descrevem busca parcial case-insensitive por nome; TXT diz nome ou slug. Comportamento de busca por slug não foi testado.
Resposta 200 `{authors:[...], cursor:string|null}`.
Exemplos de autor: `id`, `tenant_id`, `name`, `slug`, `bio`, `avatar_asset_id`, `email`, `social_links`, `created_at`, `updated_at`. Campos podem ser null conforme resposta; não extrapolar nulabilidade para requests.

### POST /v1/authors — write:authors

JSON:
- `name` obrigatório, string 1–120 caracteres.
- `slug` opcional, lowercase kebab-case; auto-gerado do nome se omitido.
- `bio` opcional, string até 2000.
- `avatar_asset_id` opcional, asset existente do mesmo tenant.
- `email` opcional, string.
- `social_links` opcional, objeto com `twitter`, `linkedin`, `website`.
Resposta 201 `{author:{...}}`. Unicidade, validação social e merge profundo não detalhados. Avatar/LinkedIn de exemplos de request e response não coincidem: não tratar discrepância de exemplo como comportamento real.

### PUT /v1/authors/:id — write:authors

Path `id` string obrigatório. JSON opcionais `name` (1–120), `bio` (string|null, até 2000), `avatar_asset_id` (string|null), `email` (string|null), `social_links` objeto. `null` pode remover avatar; nulabilidade de social_links no request não comprovada. Slug imutável após criação segundo TXT. Retorna 200 `{author:{...}}`.

### PUT /v1/authors/:id/reassign — write:authors

Path `id` autor de origem; body obrigatório `target_author_id` string de autor do mesmo tenant. Move **todos** os artigos da origem em **todos** os sites do tenant. Sem filtro por site documentado.
200 `{reassigned_count:number, site_ids:string[], source_author_id:string, target_author_id:string}`. Não remove autor de origem automaticamente. Atomicidade, falha parcial e origem=destino não especificados.

### DELETE /v1/authors/:id — write:authors

Somente autor sem artigos vinculados. Sucesso 204 sem body. Com artigos, 409 `author_has_articles`, `message`, `article_count`, `site_ids`; orientação de usar reassign antes. A orientação do fornecedor não constitui autorização para reatribuir ou apagar automaticamente.

## Categorias — site-specific

### POST /v1/categories — write:categories

JSON obrigatórios `site_id`, `slug`, `name`, strings; slug/name da tradução inicial.
Opcionais: `locale` (default locale do site); `parent_id` (string|null no screenshot, pai do mesmo site); `hidden` boolean default false; `show_in_header` boolean default false; `display_order` inteiro default 0; `icon_key` string opcional no TXT.
201 `{category:{...}}`; exemplo contém id, site_id, parent_id, hidden, show_in_header, display_order, translations[] com locale/slug/name.

### PUT /v1/categories/:id — write:categories

Path id obrigatório. Body opcional: `parent_id` string|null (null torna top-level), `hidden`, `show_in_header`, `display_order`, `icon_key` string|null. 200 `{category:{...}}`. Não há atualização de slug/nome/tradução de categoria documentada.

### DELETE /v1/categories/:id — write:categories

204 sem body. Move artigos para Uncategorized. Categorias do sistema não podem ser excluídas. Readback deve incluir artigos reassociados; não só ausência da categoria. Não há GET /categories documentado; não inventar rota para validar.

## Assets — biblioteca do tenant

### GET /v1/assets — read:assets

Query opcional `type`: `image`, `logo`, `favicon`. 200 `{assets:[...]}`. Exemplos incluem `id`, `tenant_id`, `type`, `original_filename`, `original_format`, `width`, `height`, `alt_text`, `tags` array, `variants_generated` array, timestamps.
Não há cursor ou limite de upload descritos. Variantes de exemplo: thumb, medium, large, original; não garantir todas para cada arquivo.

### POST /v1/assets — write:assets

Multipart, com boundary gerado pelo cliente:
- `file` obrigatório: PNG/JPEG/WebP/SVG.
- `alt_text` obrigatório: string, acessibilidade/SEO.
- `type` opcional: image default, logo ou favicon.
- `tags` opcional: string de tags separadas por vírgula.
201 `{asset:{...}}`. Upload de logo/favicon não implica seleção como logo/favicon ativo do site. Não há edição de asset documentada.

### DELETE /v1/assets/:id — write:assets

Exclui asset e variantes armazenadas. 200 `{deleted:true, variants_deleted:number}`. A descrição geral fala em unused, mas não documenta proteção referencial: verificar usos antes, nunca presumir bloqueio automático para asset em uso.

## Artigos e conteúdo localizado

### GET /v1/blocks/catalog — read:blocks

200 `{blocks:[{key, default_data, schema},...]}`. Catálogo live salvo integralmente em blocks-catalog.json. Não permite registrar/alterar tipos de blocos. Blocos são conteúdo renderizado, não controle global do CMS.

### GET /v1/articles — read:articles

`site_id` obrigatório. Query opcionais: `status` draft/review/published; `category_id`; `author_id`; `q` pesquisa title ou slug; `cursor`; `limit` 1–100 default 50; `order_by` default created_at (demais valores não enumerados); `order_dir` asc/desc default desc.
200 `{articles:[...], cursor:string|null}`. Itens de exemplo contêm article id/site_id/type/status/author_id/category_id/timestamps e translations[] com locale/title/slug/status.

### GET /v1/articles/:id — read:articles

Path id obrigatório; query locale opcional, default do site. 200 `{article, translation, referenced_assets}`. Conteúdo completo da tradução inclui blocks_json. Exemplo usa prose, mas prose **não** consta no catálogo live inicial.
Live GET expôs também featured_asset_id, OG, canonical_url, noindex/nofollow, focus_keyword e scheduled_at; isso comprova leitura desses campos, **não** escrita por esse endpoint.

### POST /v1/articles — write:articles

Cria shell/registro-base, sem conteúdo localizado. Body obrigatórios `site_id`, `author_id`; opcionais `category_id` string|null, `status` draft/review/published default draft; booleans `sitemap_exclude`, `list_exclude`, `hide_header`, todos default false no screenshot.
201 `{article:{...}}`. Flags devem ser explícitas conforme pedido; não supor que 201 publicou tradução ou completou deploy.

### PUT /v1/articles/:id — write:articles

Metadata opcionais: `author_id`, `category_id` string|null, `status` draft/review/published; `sitemap_exclude`, `list_exclude`, `hide_header` booleans.
200 `{article:{...}}`. Não é edição dos blocos/título. Flags controlam sitemap, listagem e header apenas; não são controle de acesso nem garantia de desindexação.

### PUT /v1/articles/:id/translations/:locale — write:articles

Path id e locale BCP-47 obrigatórios. Screenshots: body obrigatórios `slug`, `title`, `version` strings e `blocks_json` array ordenado.
**Conflito**: TXT e /llm.txt também exigem `path` relativo sem barra inicial; screenshots não listam path e response mostra path gerado (ex. 101/my-post). Não resolver por suposição antes de escrever.
Opcionais dos screenshots:
- `status`: draft/review/published; default draft. TXT mais antigo só cita draft/published.
- `excerpt`: string|null até 300 caracteres.
- `meta_title`: string|null até 70.
- `meta_description`: string|null até 300.
- `exclude_translation_locales`: `"all" | "none" | string[]`.
- `overwrite_manual_locales`: `"all" | "none" | string[]`.

Políticas de tradução (screenshots):
- Fan-out automático somente em site multilíngue, ao publicar locale default com status published e **ambos** os campos de política juntos.
- Se ambos omitidos: comportamento legado single-locale. Enviar só um é inválido conforme contrato visual.
- Escrita direta em secundário atualiza somente esse locale.
- `exclude_translation_locales: "all"`: nenhum secundário; `"none"`: todos os secundários ativos; array: excluir os listados. Array vazio **inválido** para este campo; usar none.
- `overwrite_manual_locales: "all"`: autoriza sobrescrita dos manuais entre os alvos; `"none"`: preserva manuais, que podem ficar stale; array: permitir overwrite só nos listados, se não excluídos. Não presumir que array vazio é válido/igual none: usar enum explícito conforme intenção confirmada.
- Locale excluído nunca é sobrescrito, mesmo listado na política de overwrite.

Resposta exemplo: `translation` com locale/slug/path/title/status/version/blocks_json; `translations` array de resultados secundários; `excluded_locales`; `compliance_warnings`.
Resultados exemplo: `{locale:"es",status:"queued"}` e `{locale:"fr",status:"skipped",reason:"manual_overwrite_not_confirmed"}`. Nome exato é `translations`, não translation_results. `queued` não significa pronto; faltam endpoint de jobs e SLA descritos.
`version` é string de versão (ex. v1), não há locking/rollback/concurrency contract documentado.

### DELETE /v1/articles/:id — write:articles

204 sem body. Exclui permanentemente artigo e **todas** as traduções.

### DELETE /v1/articles/:id/translations/:locale — write:articles

204 sem body. Exclui só tradução especificada; artigo permanece. Não há garantia documentada sobre exclusão de locale default, recuperação ou efeitos em URLs antigas.

## Documentação para IA

### GET /llm.txt — read:llm descrito

Texto com autenticação, endpoints, scopes e exemplos. Path singular `/llm.txt`, embora texto visual mencione llms.txt. Botão da UI usa sessão autenticada; cliente usa Bearer. Documentação live inicial repetiu o TXT e não incorporou várias novidades das imagens.

## HTTP e tratamento

- 200: sucesso com resposta.
- 201: recurso criado.
- 204: sucesso sem body (não tentar parse JSON vazio).
- 400: parâmetro/validação inválida.
- 401: chave ausente/inválida/revogada/expirada.
- 403: chave válida sem scope requerido.
- 404: recurso não encontrado.
- 409: conflito/dependência, ex. autor com artigos.
- 422: publicação bloqueada pelo compliance gate, ex. links quebrados.
- 500: servidor.
429/Retry-After e demais falhas devem ser tratados com backoff operacional seguro, embora rate limits específicos não estejam na documentação enviada.

## Não documentado — não anunciar como disponível

Gestão global do site/domínio/tema/idiomas/tagline, criação de sites, DNS, SSL, cache/CDN, ads.txt, redes GAM/AdX, anúncios globais, relatórios financeiros/receita/tráfego, usuários/roles, billing, redirects, export/restore oficial, gestão de chaves e automações/cron. Export editorial local pode ser construído via GET, mas não equivale a backup completo do site.
