# Escrita em rascunho — canário Monteralis

## Evidência e escopo

- Autorização: Rodolfo `1572412858980110378`, thread `1572259906902425653`.
- Evidência: `/root/mgs-agent/data/gaudi-av/draft-test-1572412858980110378/result.json` e `http.jsonl`.
- Alvo único: Monteralis, site `site_7978d172-b7e7-4803-a6f8-02c80cf028a6`, artigo `page_d7f5565d-b974-404d-9781-571e34dca3c3`, post_number 207, locale en.
- Em 2026-11-18 UTC, POST shell HTTP 201; dois PUTs de tradução HTTP 200; GETs posteriores HTTP 200, conferindo conteúdo integral contra o payload.
- Quatro blocos validados pelo JSON Schema vigente: heading, paragraph, button, accordion com mode faq. IDs de blocos preservados entre v1 e v2. Texto, label e href alterados e conferidos.
- Estado final: artigo e tradução draft; deploy_status idle; published_at null; sitemap_exclude=true; list_exclude=true. Título `[TEST - DO NOT PUBLISH] Gaudi API draft validation`.
- Inventário paginado antes/depois: 97 → 98, somente um ID adicionado; entradas da listagem dos 97 artigos existentes idênticas. Isso não é auditoria integral de cada conteúdo existente.
- Sem publicação, exclusão, alteração de monetização ou escrita no Belverica. Prévia visual não validada; sem endpoint de preview documentado ou sessão administrativa usada neste teste.

## Shell ainda sem tradução

Após POST 201, GET /v1/articles/:id?locale=en retornou 404 com mensagem referindo artigo **in locale en**, e a listagem draft não expôs esse shell. Após criar a primeira tradução no mesmo ID, GET e listagem passaram a encontrá-lo.

**Preserve o ID do POST antes de qualquer chamada posterior. Não conclua que o shell não existe, nem repita POST, por causa desse 404 ou de ausência na listagem sem tradução.** Confira o recibo 201 e o histórico de escritas; se o shell foi criado e a tradução nunca foi enviada, preencha a tradução autorizada no mesmo ID. Timeout/resultado ambíguo de POST permanece bloqueado para replay sem prova de ausência.

## Contrato de path: comprovação limitada

O PUT aceitou `path` explícito relativo, igual ao slug `gaudi-api-draft-test-1572412858980110378`, sem barra inicial, e GET devolveu o mesmo valor tanto em v1 como v2. Isso comprova esse formato para o canário. **Não comprova que path é obrigatório, que pode ser omitido ou que o sistema prefixa URLs.** Para novos rascunhos equivalentes, enviar path explícito validado. Não testar mudança/omissão em URLs existentes por conveniência.

## Limite de permissões

Criação de shell e criação/edição de tradução em draft estão comprovadas para a chave Monteralis nesse alvo. Publicação, exclusão, assets, autores/categorias e escrita na chave Belverica continuam não exercitadas. Não anunciar write:* global por esse teste. O rascunho foi preservado, sem cleanup implícito.
