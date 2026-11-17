---
name: gaugi-av
description: "Use when operating Gaudi AV. Check scopes and site limits."
version: 0.1.0
author: Rodolfo Mattei, Zeus
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [gaudi, gaugi, active-view, cms, api, content, mgs]
---

# Gaudi AV — operação segura da Public API

Nome solicitado por Rodolfo: `gaugi-av`; produto/documentação: **Gaudi**, da Active View. Esta skill reúne a documentação enviada, diferenças entre fontes, catálogo real de blocos e evidência de leitura das duas credenciais. Não é permissão permanente para publicar ou alterar os sites.

## When to Use

- Consultar ou operar o CMS Gaudi dos domínios autorizados por Rodolfo.
- Inventariar artigos, autores, mídias, categorias observáveis e idiomas.
- Planejar conteúdo por blocos, páginas de oferta/landing pages, traduções e SEO.
- Diferenciar capacidades do painel, endpoints documentados e permissões efetivamente comprovadas.
- Não confundir esta API de conteúdo com APIs de receita, GAM, configuração de anúncios, WordPress, DNS ou hospedagem.

## Fontes e arquivos

1. `references/api-reference.md`: contrato consolidado completo, campos, endpoints, erros, limites e políticas multilíngues extraídas das imagens.
2. `references/documentation-conflicts.md`: divergências obrigatórias antes de qualquer escrita.
3. `references/vendor-message-txt.md`: TXT fornecido por Rodolfo, com placeholders de autenticação normalizados para não parecerem credenciais.
4. `references/vendor-live-llm.txt`: `/llm.txt` obtido com GET autenticado; snapshot documental, não verdade superior ao runtime.
5. `references/blocks-catalog.json`: catálogo real completo, incluindo JSON Schemas e `default_data` dos 19 blocos observados.
6. `references/blocks-guide.md`: resumo operacional de cada bloco e cuidados.
7. `references/read-only-validation.json`: resultados autenticados por credencial, sem valores secretos.
8. `references/article-summary.json`: contagem paginada e campos de um artigo amostrado por domínio, sem copiar os artigos.
9. `references/source-manifest.json`: origem e integridade dos documentos/imagens.
10. `assets/source-screenshots/`: todas as imagens fornecidas nesta sequência, preservadas como evidência (não especificação executável).

## Pré-requisitos e autoridade

- Validar identidade, thread, domínio-alvo e autoridade atual em `AGENT.md`, `data/authorized-users.json` e fontes MGS. Nenhuma chave concede autoridade organizacional.
- API base exata: `https://mosaic-api-1453299254.us-east1.run.app`.
- Header: `Authorization: Bearer <API_KEY>`; credenciais exclusivamente no 1Password, em memória durante a chamada. Nunca em argv, logs, arquivos, skill, screenshots novos, Git ou chat.
- Obter item via wrapper canônico `/root/mgs-agent/scripts/mgs-op-with-service-account.sh item get <item-id> --vault <vault-id> --format json`, usando `subprocess.run(..., capture_output=True)` dentro de Python e selecionando o campo `credential`. Nunca imprimir o JSON bruto.
- Vault: `ghkdcenuzsp57w37nzhxuxnkj4`.
- `monteralis.com`: item `tsdpzpljypmchmqkte5mpmw7a4`, título `Gaudi - monteralis.com`; site observado `site_7978d172-b7e7-4803-a6f8-02c80cf028a6`.
- `belverica.com`: item `ac3wyr7to2wwdsanogftrl6bry`, título `Gaudi - belverica.com`; site observado `site_316408ba-a45e-4b9b-9b78-a0994b04bbd7`.
- IDs são referências de descoberta, não substituem readback atual. Ambas as chaves retornaram apenas o respectivo site em `/v1/sites` na validação inicial. Não inferir que são chaves tecnicamente site-scoped: o contrato é **tenant-scoped**.
- Nunca enviar `tenant_id` nas requisições. Autores e assets são compartilhados no tenant. `reassign` afeta todos os sites do tenant, sem filtro de site documentado.
- Criação de skill não altera autorização de Atena/Ares nem instala cópias em outros perfis. Produção editorial segue o responsável e autorização vigente; Zeus não assume produção editorial por padrão.

## Procedimento de leitura

1. Fixar domínio exato, objetivo e endpoints autorizados. Selecionar o item correto por ID e título.
2. Ler a credencial em memória. Usar cliente HTTPS sem redirecionar Authorization para outro host; desabilitar redirects autenticados ou rejeitar redirecionamentos. Nunca usar `curl -v` ou tracing de headers.
3. Executar `GET /v1/sites`; exigir que o domínio exato corresponda a um único site. Se surgirem outros sites, não operar/enumerar conteúdo fora do escopo autorizado.
4. Consultar somente os recursos necessários, com timeouts, paginação por cursor opaco e limites explícitos. Para todos os itens, acumular em JSON, deduplicar IDs, contar em código e confirmar cursor final nulo. Não chamar amostra de inventário completo.
5. Antes de construir conteúdo, atualizar `GET /v1/blocks/catalog`. `key` define `type`; validar `data` pelo JSON Schema real. `default_data` é ponto de partida e pode ser inválido enquanto contiver campos vazios.
6. Para artigo, `GET /v1/articles/:id?locale=<locale real>` retorna `article`, `translation`, `referenced_assets`. Confirmar `article.site_id` e nunca assumir `en-US` quando site retorna `en`.
7. Reportar por credencial: endpoint, HTTP e capacidade observada. Leitura 200 não prova `write:*`; não há endpoint de introspecção de scopes documentado. Não usar POST/PUT/DELETE inválido como teste de permissão.

## Procedimento de escrita — somente após pedido autorizado

1. Ler `references/documentation-conflicts.md`. Não executar escrita enquanto contrato de `path`, bloco ou locale estiver ambíguo. Confirmar no fornecedor/contrato atualizado ou em canário explicitamente autorizado; nunca testar em artigo existente por conveniência.
2. Delimitar IDs, campos, idiomas, publicação e possível fan-out. Guardar antes/depois e plano reversível, sem segredos. Não modificar loaders/monetização protegida por associação com o CMS.
3. Confirmar scopes de escrita por evidência do painel ou operação real autorizada; `write:*` e `read:*` não são implicitamente equivalentes.
4. Para novo conteúdo, criar shell com status explícito `draft`, flags explícitas e autor/site/categoria verificados. Persistir o ID retornado; falha posterior não autoriza criar outro shell.
5. Enviar a tradução com slug, title, version e blocos validados, mais o contrato de path confirmado. Preservar IDs estáveis dos blocos existentes. Metadata e tradução são camadas distintas; verificar ambas.
6. Publicar somente se o pedido incluir publicação. Multilíngue: nunca habilitar ou sobrescrever idiomas adicionais sem escopo explícito. Omitir ambos os campos de fan-out mantém single-locale conforme screenshots; se habilitado, enviar os dois juntos e preservar manual com `overwrite_manual_locales: "none"`, salvo autorização contrária.
7. Tratar warnings de compliance e HTTP 422 sem bypass. `queued` não é tradução pronta; `skipped` não é sucesso integral. Não prometer conclusão de deploy/tradução com base só em resposta 200.
8. Readback exato por API; publicação exige conferir URL retornada e render público, idioma, links, status e deploy real. Não presumir rota a partir do slug. Não tratar sitemap_exclude/list_exclude como autenticação ou garantia de noindex.
9. Exclusões e outras ações críticas passam pelo Critical Subset/confirmação adicional aplicável, incluindo aprovação explícita do alvo e efeitos colaterais. Nunca excluir como cleanup implícito de um canário ou falha.

## Recuperação e idempotência

- Primeira falha: diagnosticar e aplicar recuperação segura na autoridade vigente; 401/403 não autorizam rotacionar chave ou ampliar scopes.
- 400: corrigir contrato validado; 409: reconciliar dependência; 422: corrigir compliance, sem bypass; 429: respeitar Retry-After; 5xx/timeout: backoff limitado e readback antes de retry.
- Após timeout de POST/PUT/DELETE, reconciliar efeitos antes de repetir. Não há idempotency-key documentado. Não inventar transações, locking otimista, versionamento com rollback ou garantias exactly-once.
- Interromper tentativas cegas após cinco falhas consecutivas da mesma ferramenta, antes em loop. Preservar IDs, checkpoint, dono e dependência/retomada real.

## Limites comprovados

- API documentada cobre conteúdo e parte da navegação/visibilidade, não administração integral do site.
- Não documentados: criar/excluir site, trocar domínio/idiomas/tagline/config global, tema/CSS global, usuários/permissões, DNS/SSL, redirects, ads.txt, GAM/AdX, receita/tráfego, billing, backups/restores, cron de publicação, gestão das próprias chaves pela API.
- Upload `type=logo/favicon` cria mídia; não prova aplicação como identidade global do site.
- Bloco `custom-html` não prova execução de JavaScript arbitrário, controle de head/global ou autorização de pixels/anúncios.
- GET pode expor canonical/noindex/OG/scheduled_at sem oferecer escrita documentada desses campos.
- Snapshot inicial: todas as leituras testadas funcionaram nas duas chaves; nenhuma escrita foi executada ou comprovada.

## Verificação e entrega

- Skill e arquivos vinculados existem e estão legíveis; schemas e inventários parseiam; nenhum token real foi gravado.
- Contagem dos blocos calculada e única; origens, contratos conflitantes e limites explícitos.
- Ler permissão efetiva separadamente de capacidade documental; nunca anunciar controle integral nem scopes de escrita sem evidência.
- Registrar skill em inventário `skills_hermes.zeus`, registry institucional, audit e REPORT-INFRA canônico; sincronizar apenas esta skill para espelho Zeus, sem tocar perfis de terceiros.
- Resposta normal na thread atual: capacidades práticas, validações reais, lacunas e próximo bloqueio, sem anexos não solicitados.
