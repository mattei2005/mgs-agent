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

### Páginas Elementor

Trate `_elementor_data` como estado de builder, não como prova de frontend. Um PUT pode retornar `200` e o GET autenticado repetir o JSON novo enquanto o HTML público continua vindo de `post_content` renderizado ou cache antigo. Preserve o JSON completo, altere somente os widgets identificados, mantenha IDs/mídia/configurações e tente primeiro o fluxo de save/regeneração suportado pelo Elementor.

Não presuma que `Plugin::$instance->db->save_editor()` ou `Document::save()` exista ou aceite o payload naquela versão: valide a API por reflection/read-only e pare se o método não estiver confirmado. Se o builder não oferecer um save programático funcional, use fallback reversível somente com autorização e preservação comprovada: salve `_elementor_data`, `_elementor_edit_mode` e `post_content`; derive o novo `post_content` do fragmento renderizado existente, removendo demo e mantendo mídia, links, formulário e CTA; mantenha o `_elementor_data` editado para futura retomada; limpe `_elementor_edit_mode` explicitamente para o frontend usar o `post_content`; purgue apenas a página. Exija readback REST e DOM público em desktop/mobile antes de aceitar o fallback. Nunca envie HTML genérico que descarte a estrutura existente.

Depois, valide H1, texto, widgets, imagens e formulário no DOM público; não declare sucesso pelo meta readback isolado.

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

## 7. Corrija metadata protegida antes do cutover

Não remova `noindex` enquanto qualquer alvo tiver metadata ausente, antiga ou não verificável.

1. Consulte `OPTIONS /wp-json/wp/v2/<post_type>/<id>` e confirme se `schema.properties.meta` existe.
2. Se o CPT não expõe `meta`, trate HTTP `200` de um PUT como inconclusivo: o core pode ignorar `_yoast_wpseo_title`, `_yoast_wpseo_metadesc` e `_yoast_wpseo_focuskw` e ainda alterar `modified`.
3. Exija GET/post meta e HTML público iguais ao payload esperado. Se a rota Yoast bulk/editor retornar `403`, pare antes do cutover.
4. Só use WP-CLI ou banco por um caminho privilegiado autorizado, com snapshot dos valores, rollback escopado e readback dos três campos para todos os IDs.
5. Atualize primeiro a metadata inteira; valide que todos os alvos continuam `noindex`; só então inicie a mudança de robots.

### Caminho privilegiado temporário

Quando a correção exigir WP-CLI em RunCloud e o servidor não tiver uma chave persistente autorizada:

1. Trate a criação da chave como Critical Subset e obtenha confirmação específica.
2. Confirme por API a identidade exata de servidor/webapp/root path e exija contagem inicial de credenciais `0`. Se já existir uma credencial temporária, não crie outra: leia apenas ID/label/estado seguro, aguarde o owner encerrar o ciclo e refaça o preflight; duas chaves concorrentes tornam rollback e autoria ambíguos.
3. Gere uma chave Ed25519 efêmera em diretório `0600`, cadastre-a como `temporary=true`, valide readback e use `BatchMode=yes`.
4. Faça snapshot remoto antes de qualquer meta/plugin write. Compare SHA do arquivo live com o esperado; mismatch encerra o write.
5. Se o mismatch mostrar que a candidata partiu de versão histórica, remova a credencial, baixe o arquivo live em um novo ciclo somente leitura e reconstrua/teste a candidata a partir dele.
6. No `finally`, apague a credencial pela API, exija GET `404`, remova a chave local e confirme a contagem final `0` — inclusive após falha ou rollback.

Nunca mantenha a chave aberta entre turnos para “facilitar” a validação; a mesma rotina deve fechar credencial e material local antes de retornar.

## 8. Faça o cutover como uma transação de lote

1. Capture a política ativa e seu SHA antes da alteração. Gere a candidata a partir do arquivo **live exato**, não de uma cópia histórica: hash inesperado é gate de parada, porque um patch sobre versão antiga pode apagar hardening posterior.
2. Se um MU plugin protege um post type inteiro, introduza uma allowlist determinística dos IDs aprovados antes da regra ampla de bloqueio.
3. Para sitemaps, não basta liberar o post type: exclua dinamicamente todos os registros do tipo que não estão na allowlist. Preserve arquivos, taxonomias e outros CPTs protegidos.
4. Lembre que o sitemap de um CPT pode incluir a URL do archive além dos itens singulares; valide o conjunto esperado como `archive + IDs aprovados`, não apenas os singulares.
5. Corrija metadata do archive se ele passar a entrar no sitemap. Se um archive/paginação expõe cards demo, `noindex` sozinho não corrige a experiência pública: restrinja a query aos IDs aprovados e redirecione paginação stale para o archive canônico; se o archive continuar protegido, mantenha-o fora do sitemap.
6. Faça purge somente dos IDs/URLs e sitemaps afetados. Limpe o cache de sitemap do Yoast quando disponível.
7. Valide, em ordem: metadata pública ainda sob `noindex` → deploy da allowlist → `index,follow`/headers/canonical dos alvos → inclusão no sitemap → crawl de todas as URLs dos sitemaps → browser desktop/mobile.
8. Em qualquer falha pós-deploy, restaure o arquivo anterior, purgue os mesmos alvos e prove o retorno de todo o lote a `noindex,nofollow`.

## 9. Audite o site além dos sitemaps

Um sitemap 100% verde não prova que o site inteiro está limpo. Faça crawl interno same-origin e classifique separadamente:

- URLs finais `200` indexáveis;
- páginas `noindex` intencionais;
- redirects — compare canonical com a URL **final**, não com o alias solicitado, para evitar falso não-canônico;
- paginação indexável fora do sitemap;
- conteúdo demo indexável;
- URLs indexáveis ausentes do sitemap e URLs do sitemap não indexáveis.

A varredura de conteúdo demo deve usar um léxico amplo e inspecionar o HTML renderizado, não apenas `Lorem ipsum`. Inclua famílias como `Sed ut perspiciatis`, `Adipiscing elit`, `Dicta sunt`, `Natus error`, `Consetetur/Sadipscing`, autores/captions fictícios e contadores placeholder. Refaça o crawl depois de cada correção material: remover dois resíduos pode revelar outro que o primeiro padrão estreito não detectava.

Não amplie automaticamente o escopo para páginas descobertas no crawl. Reporte-as com URL e classificação e obtenha decisão para reescrever, redirecionar ou aplicar `noindex`.

## 10. Search Console pela identidade Google canônica

Use apenas a Service Account corporativa e o escopo read-only do Search Console. Filtre a resposta para a propriedade-alvo; não enumere propriedades externas nem use conta pessoal como fallback.

- API de sites: `https://www.googleapis.com/webmasters/v3/sites`
- Escopo: `https://www.googleapis.com/auth/webmasters.readonly`
- Inspeção de URL, sitemaps e analytics só depois de confirmar acesso à propriedade.

Se `searchconsole.googleapis.com` estiver desativada no projeto ou a Service Account não tiver acesso, confirme o estado também pela Service Usage API, reporte projeto/serviço/bloqueio e conclua apenas a auditoria pública de readiness. Não habilite API global, conceda acesso à propriedade nem envie indexação manual sem autorização própria.

Para diagnosticar `Couldn't fetch` em sitemap sem adivinhar:

1. teste index + filhos com browser, Googlebot, Google-InspectionTool e cliente comum;
2. exija HTTP `200`, XML parseável, `text/xml`, ausência de challenge e robots.txt acessível;
3. consulte `sites`, `sitemaps` e URL Inspection pela propriedade exata;
4. use `errors`, `warnings`, `isPending`, `lastDownloaded` e inspeção individual como evidência principal.

Os contadores `submitted/indexed` do relatório de sitemap podem ficar defasados em relação ao XML live e à URL Inspection. Se `errors=0`, fetch público passa e as inspeções retornam `PASS`/`INDEXING_ALLOWED`/`SUCCESSFUL`, reporte processamento assíncrono em vez de reenviar o sitemap sem instrução. Diferencie sempre “tecnicamente indexável”, “inspecionado como permitido” e “contador agregado já atualizado pelo Google”.