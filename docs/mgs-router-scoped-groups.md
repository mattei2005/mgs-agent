# MGS Router — Campanhas e Landing Pages: grupos independentes

## Autoridade e supersessão

Rodolfo autorizou na mensagem `1556447468928106520` (thread `1555381168894115912`) a proposta `1556384265288159312`: organização como a referência Keitaro, **incluindo separação real dos cadastros de grupos**, não só alteração visual.

Esta fonte sucede a organização global de grupos de `docs/mgs-router-catalog-layout.md`, `docs/mgs-router-group-edit-and-wantabrand-cutover.md` e a parte de grupos de `docs/mgs-router-owner-exceptions-1556362463413276675.md`. Não sucede decisões de tráfego, DNS, destinos reparados/aposentados, sessão, noindex ou favicon. Tracking/relatórios/postbacks continuam fora de escopo.

## Publicado e conferido

- Menu: **Campanhas**, **Landing Pages**, **Cadastro domínios**. A aba global Grupos foi retirada.
- Campanhas (antigas Rotas): Criar, Grupos, filtro Todos os grupos, filtro de domínio e busca.
- Landing Pages (antigos Destinos): Criar, Grupos, filtro Todos os grupos e busca.
- Cada botão Grupos abre modal próprio com nome, quantidade de itens dessa área, criar, editar nome e excluir. A quantidade clicável filtra a lista correspondente. Modal fecha por botão ou Escape.
- Renomear/excluir um grupo altera só seu cadastro e as associações da sua área, sob revisão atômica. Mesmo nome pode existir nas duas áreas. Excluir deixa os itens sem grupo; não apaga links, URLs, IDs nem pesos.

## Modelo e migração

`routes.json` usa `group_schema: 2`, `route_groups` e `destination_groups`, ambas listas obrigatórias, inclusive quando vazias. `groups` global não participa do estado migrado. Backend valida pertinência por área, referências de destino, duplicatas e versão; rejeita downgrade/payload antigo e revisão stale depois da migração.

Migração publicada de revisão 40 para 41: **445 campanhas, 943 Landing Pages, 29 grupos em cada cadastro independente**. Os 29 nomes atuais foram copiados para ambos os cadastros para preservar todas as associações e grupos vazios, sem restaurar nomes históricos nem inferir nova classificação. Isso preserva a organização local existente; não é uma nova importação da atribuição interna de grupos do Keitaro.

As listas de rotas e catálogo foram preservadas **exatamente**, incluindo nomes, memberships, hosts, paths, URLs, ordem de destinos, IDs, pesos, modos de query e a resposta500 histórica. Nenhuma escrita em DNS, SSL, WordPress, credenciais, permissões ou gateways.

## Evidência real

- 67 casos/subcasos Go PASS; race detector, vet, sintaxe JS e build PASS. Teste RED inicial confirmou ausência dos novos campos.
- Chromium local: criação de nomes iguais nas duas áreas, renomear/excluir isolados, contagens, cancelar exclusão, concorrência/stale, recarregar, catálogo compartilhado, URLs/pesos, grupos vazios, mobile e logout. Dados sintéticos somente em fixture local.
- Chromium público Rodolfo/Geizian: modal correto em cada área, 29 grupos e contagens conferidos contra API, filtros, formulários/editor de grupo com cancelamento, exclusão cancelada, reload, mobile sem overflow do documento, 19 domínios verdes, sessão mantida após avanço do relógio9h. Zero POST de UI e zero erros JavaScript.
- **1.856 verificações públicas** de GET/HEAD, com/sem query e caminhos reservados: todas passaram para a configuração esperada. Fidelidade do redirect não significa que os destinos históricos404 estejam recuperados; os91 destinos404 previamente documentados continuam fora desta alteração.
- Formulário nativo vazio confirmou Origin same-origin e303 de credencial ausente; HTTP autenticado confirmou login/API/logout separado. Origin null/estrangeira403; API anônima401; origem direta403; painel inacessível nos hosts de tráfego.
- Serviço Router active/running como mgs-router com limites e sandbox anteriores. PIDs de Zeus/Atena/Ares, usuários e unidade preservados. Cache de domínios preservado no deploy; o verificador canônico posterior consultou os19 hosts online novamente e renovou somente seus resultados/timestamps.

## Artefatos e rollback

- Código: `apps/mgs-router/main.go`, `catalog.go`, `scoped_groups_test.go`, `web/admin.html`, `web/app.js`, `web/style.css`.
- QA local: `apps/mgs-router/tests/browser_smoke.py`; público: `tests/public_scoped_groups_smoke.py`.
- Executor restrito a esta aprovação: `scripts/mgs-router-scoped-groups-deploy.py`.
- Verificador canônico atualizado para selecionar smoke por `group_schema`: `scripts/mgs-router-verify-public.py`.
- Receipt: `data/mgs-router-scoped-groups-validation.json`; verificação de segurança/serviço posterior: `data/mgs-router-public-validation.json`.
- Par binário/estado rollback privado: `/root/.local/share/mgs-router-rollbacks/1556447468928106520/`. Binário anterior + estado anterior e binário candidato + estado candidato exercitados via `--check`; checksums registrados. Dados privados fora do Git.
- Restaurar binário antigo sozinho não é rollback válido após a migração: ele não entende os cadastros independentes. Restaurar o par somente após reconciliar edições posteriores; executor automático faz rollback apenas quando encontra exatamente o baseline ou o estado esperado. Não reaplicar executor com receipt existente.
- Só o Router foi reiniciado; sessões anteriores podem precisar de um novo login por causa do deploy. A política sem logout por tempo/inatividade e botão Sair permanecem iguais.

## Falhas intermediárias recuperadas antes da produção

Checkpoint com caminho relativo incorreto corrigido para absoluto; wrapper read_file retornou dedup sem conteúdo e foi reconciliado; CSS teve leitura de linhas longas truncadas e foi editado por patch, não sobrescrita incompleta. Preflight RED de metadata legado ajustado para a migração explícita schema2. QA detectou catálogo omitido em fixture vazio: operações de grupo tratam lista ausente como vazia. Assertions aguardam texto real da linha, não quantidade1 que também pode ser placeholder. Suíte completa repetida verde antes da publicação; nenhuma falha produtiva na entrega.
