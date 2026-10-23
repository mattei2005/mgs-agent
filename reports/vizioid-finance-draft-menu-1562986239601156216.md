# Vizioid — financeiros em rascunho e menu mobile corrigido

## Autoridade e escopo

- Rodolfo `1562986239601156216`, áudio: não manter conteúdo financeiro no Vizioid; colocar em rascunho.
- Rodolfo `1562986573576937582`, mensagem em steer com duas imagens: corrigir no WordPress o menu que abre vazio no celular.
- Único domínio alterado: `vizioid.com`. Outros cinco domínios SHEIN não foram modificados neste pedido.
- Evidência detalhada: `/root/.hermes/profiles/zeus/reports/vizioid-finance-draft-1562986239601156216/`.

## 1. Conteúdo financeiro

Inventário live: 236 artigos publicados. Revisados todos os títulos, categorias e slugs; corpo lido nos casos ambíguos. Alvo congelado: **204 artigos financeiros**, incluindo empréstimos pessoais/automotivos, investimentos, orçamento, aposentadoria, impostos e planejamento financeiro. Os 53 citados na auditoria anterior eram somente o piso por títulos/slugs de cartão/empréstimo, não o total financeiro.

Preservados **32 artigos**: os 30 de Fashion/Trends (SHEIN, moda, compras, tecnologia e lifestyle) e dois guias antigos com foco em compras/produtos (`8460`, `7796`), apesar da categoria legada Finance. Não usar categoria isolada para converter esses dois em falsos positivos financeiros; não foi alterada a taxonomia neste escopo.

Backup completo antes da transição: `/home/runcloud/mgs-backups/vizioid-finance-draft-1562986239601156216/database-before.sql` no MatteiInc03JBF, 49.012.214 bytes, SHA-256 `4b56d84aa2c52724b7783204940fd7e1c3891a870f280b1b044c60fd518d30e4`. Snapshots de posts/páginas, hashes, menus, theme mods e widgets preservados localmente; sem exclusão de dados.

Aplicação nativa WordPress, canário `8065` primeiro e depois o conjunto congelado, com readback de status. WP Fastest Cache foi omitido apenas no processo CLI mutante para evitar que seus hooks excluíssem arquivos; caches afetados foram arquivados reversivelmente fora do webroot, com SHA-256.

Validação independente:
- 204/204 alvos em `draft`.
- Conteúdo/excerpt, IDs, slugs, títulos, datas originais, autores e termos dos alvos preservados. Apenas status e timestamps de modificação nativos mudaram.
- Todos os registros não alvo preservados; 32 artigos continuam publicados e HTTP 200 com marcador de ID correto.
- 204 URLs públicas deixam de servir os artigos: 165 dão 404 diretamente; 39 têm redirect legado 301 para `?p=ID` que termina em 404. Nenhum HTML-alvo continua público. Redirects não foram alterados, pois não são necessários para retirar o conteúdo e não houve autorização específica para redesenhá-los.
- Sitemap público atual tem 33 URLs (32 artigos + home), nenhum dos 204 alvos. Os dois sitemaps do Vizioid foram reenviados, com PUT 204 e GET 200 no alvo exato.
- Google pode manter resultados históricos até recrawlear; não foi prometida remoção imediata do índice.

## 2. Menu mobile vazio

Causa confirmada: o tema JBF abre o painel `#jd-drawer` corretamente, mas seu conteúdo depende exclusivamente da sidebar `jbf_server_drawer`, que estava vazia. O menu principal existia com Home/Fashion/Trends/Contact; a atribuição desktop não popula o drawer.

Correção feita **dentro da configuração nativa do WordPress**, sem editar tema, JS ou criar menu duplicado:
- Criado widget nativo Navigation Menu `nav_menu-1`.
- Ligado ao menu principal existente `209`.
- Atribuído somente a `jbf_server_drawer`.
- Preservados todos os outros widgets, menus e locais de navegação.
- Cache do header antigo arquivado reversivelmente, com hashes. Nenhum arquivo excluído.

Validação Chromium real:
- 320, 390, 430 e 1280 px: abre/fecha corretamente.
- Quatro links visíveis, texto branco legível e zero overflow horizontal.
- Clique real em Fashion chega a `/category/fashion/`.
- Home, Fashion, Trends e Contact: 4/4 HTTP 200, widget presente no HTML público sem cache-buster.

## Recuperações intermediárias

O canário inicialmente estava draft no banco, mas a URL com e sem query ainda servia HTML antigo de cache WPFC. `?p=8065` retornava 404 e provou que a transição de estado estava correta. Após arquivar o cache e as páginas que o referenciavam, as URLs bare/query deram 404; só então o lote foi expandido. Na validação final, redirects 301 foram seguidos e tiveram 404 final, evitando falso alerta de artigo ainda publicado.

## Continuidade

Decisão sem finanças persistida em `context/acquisition.md`, seção Vizioid — escopo editorial sem finanças, e registro `vizioid-editorial-no-finance-1562986239601156216`, chave `acquisition.vizioid.editorial-finance-policy`. Validar o registry pelo helper canônico antes do encerramento.

Procedimento reutilizável de drawer salvo na skill `wp-plugin-mass-operation/references/jbf-empty-mobile-drawer-native-widget.md`.

Este relatório sucede a pendência decisória do Vizioid na auditoria `reports/shein-seo-indexing-1562978784418996264.md`. Seus números de 236 artigos e indexação eram baseline histórico anterior à quarentena, não inventário ativo atual. Não certifica que todas as pendências SEO dos seis domínios foram resolvidas.
