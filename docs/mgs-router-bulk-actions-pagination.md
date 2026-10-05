# MGS Router — ações em lote, lista compacta e paginação

## Autoridade e fonte ativa

Rodolfo pediu seleção como Keitaro e botões lado a lado em `1556466018472431646`; confirmou os efeitos reais de Ativar/Desativar e exclusão protegida em `1556468187678117921`. Durante execução acrescentou **30 itens por tela com próxima página**, tanto em Campanhas quanto Landing Pages, em `1556474705412624385`. Thread: `1555381168894115912`.

Esta fonte acrescenta/sucede os detalhes da interface em `docs/mgs-router-scoped-groups.md`: grupos continuam independentes, `group_schema:2` permanece, assim como contratos de query, destinos, DNS, sessão e privacidade anteriores. Não há tracking, postbacks ou relatórios de cliques.

## Publicado e validado

1. **Campanhas, Landing Pages e grupos de cada área**: checkbox por item, selecionar todos os itens visíveis, destaque da linha selecionada e barra **Excluir, Clonar, Ativar, Desativar, Limpar seleção** com quantidade selecionada.
2. **Campanhas e Landing Pages**: **30 itens por página**, Anterior/Próxima e Página X de Y. Páginas independentes por aba; filtros, busca e ordenação reiniciam na página1; mudanças de página descartam seleção de itens que deixam de estar visíveis. Grupos continuam em seu modal por área, não recebem paginação neste pedido.
3. **Lista compacta**: Editar destino/Copiar link lado a lado, padding/intervalos reduzidos e estados por indicador. Tabelas largas continuam com rolagem interna; documento não transborda no celular.

## Efeitos das ações

- Campanha desativada retorna404, sem Location, mantendo proteção no-store/referrer e sem excluir configuração. Ativar restaura o tráfego configurado. A resposta500 de origem Keitaro permanece500 quando ativa e404 quando desativada.
- LP desativada é excluída apenas da seleção efetiva por **destination_id**. Pesos, ordem e URLs armazenados não mudam: os destinos ativos restantes recebem proporcionalmente aos pesos; sem destino ativo, retorna404 sem redirect. Uma URL manual sem referência de catálogo não é desativada por outra identidade de LP que compartilhe a URL.
- Ativar/Desativar grupos altera os membros **daquela área**, sem mudar o cadastro de grupos da outra área. Um grupo vazio não produz alteração; grupo com estados diferentes mostra Misto.
- Excluir campanha retira o registro do Router, não arquivos WordPress nem DNS. Excluir grupo retira a organização e limpa apenas memberships daquela área: não apaga membros/URLs/IDs/pesos/estados.
- Excluir LP utilizada é bloqueado **no frontend e no backend**, inclusive a tentativa de remover a LP e suas referências no mesmo payload. Primeiro retirar referências; depois excluir. Em seleção mista com LP utilizada, a exclusão inteira é bloqueada, sem efeito parcial.
- Clonar gera identidade independente: campanha recebe caminho novo e único no mesmo host, preservando destinos, IDs/pesos/query; LP recebe ID novo com mesma URL. Grupo clonado recebe nome único e cópias de seus membros. **Todas as cópias começam desativadas**, sem tráfego inesperado; originais ficam intactos. O diálogo informa efeito e quantidade antes de cada ação.
- Estado editor de campanha/LP é preservado em saves; desativar LP no editor também informa impacto nas campanhas antes de aplicar.

## Modelo e compatibilidade

`Config.action_schema:1`, `Route.disabled` e `Destination.disabled` (false/ausente=ativo). Backend rejeita versão desconhecida, flags de estado sem action schema e downgrade/payload antigo depois da migração. Writes conservam revisão atual, ambos os grupos, catálogo e rotas; concorrência stale não aplica mutação parcial.

Backend mantém `cfg` com a configuração original e constrói somente uma cópia efetiva do índice de tráfego, filtrando LPs inativas por ID. Reativação não exige reconstruir pesos salvos. Catálogo e aliases continuam com as validações anteriores.

## Baseline e implantação

- **445 campanhas, 943 LPs, 29 grupos em cada área**, todos os estados anteriores mantidos. Nenhuma campanha/LP/grupo existente foi clonado, excluído, ativado ou desativado no teste público.
- Primeira implantação acrescentou action_schema1 por API, revisão41→42, com listas de rotas/catalog e grupos exatamente preservadas.
- Segunda implantação acrescentou paginação **apenas no código**, preservando inclusive a revisão42 e hash do estado de rotas. Somente o serviço Router reiniciou; gateways, usuários, permissões, credenciais, DNS, SSL e WordPress não foram alterados. Sessões anteriores podem pedir novo login por restart; política sem logout por tempo/inatividade e Sair mantidas.

## Evidência real

- **73 casos/subcasos Go**, race detector, vet, sintaxe JS e build PASS. RED confirmou campos disabled ausentes e, depois,65 registros na tela antes de limitar30.
- Chromium local + API real em estado isolado: quatro ações, ambos os grupos, clones desligados com identidade/caminho novo, exclusão protegida e stale, cancelamento, reativação, efeito404/302, peso30/70 preservado e LP ativa restante recebendo100%, URLs/query intactas, grupos vazios, botões horizontais e mobile.
- Fixture65 campanhas/61 LPs: páginas30/30/5 e30/30/1, independência entre abas, última página parcial, filtro/busca com reset, seleção somente na página, índice correto do editor, reload e mobile; zero writes de API.
- Chromium público **Rodolfo e Geizian**: seleções e quantidades, quatro botões com confirmação cancelada, proteção de exclusão de LP usada, modais/filtros, reload, botões horizontalmente alinhados, mobile sem overflow e zero JavaScript errors/POST de UI. Percorridas **todas as páginas**, conferindo conjuntos e contagens exatas das445 campanhas e943 LPs em cada conta, sem duplicatas ou perdas.
- Última release: **1.856 verificações públicas GET/HEAD/query/reservados**, todas PASS. Isso prova redirects esperados, não recuperação dos91 destinos404 históricos que continuam fora deste escopo.
- HTTPS/login/API/logout, transporte nativo vazio (same-origin303), origens null/estrangeira403, API anônima401, origem direta403, painel bloqueado em host de tráfego, serviço sandbox/limites e PIDs de agentes preservados.19 verificações de domínio verdes mantidas; verificador canônico posterior renova somente observações/timestamps.

## Artefatos e rollback

- Código: `apps/mgs-router/main.go`, `routes.go`, `web/admin.html`, `web/app.js`, `web/style.css`.
- Testes: `bulk_actions_test.go`, `bulk_browser_test.go`, `pagination_browser_test.go`, `tests/bulk_browser_smoke.py`, `tests/pagination_browser_smoke.py`, `tests/public_scoped_groups_smoke.py`.
- Executors de aprovação única: `scripts/mgs-router-bulk-actions-deploy.py` e `scripts/mgs-router-pagination-deploy.py`.
- Receipts: `data/mgs-router-bulk-actions-validation.json`, `data/mgs-router-pagination-validation.json`; verificador canônico: `scripts/mgs-router-verify-public.py`/`data/mgs-router-public-validation.json`.
- Pares rollback privados exercitados com `--check`: `/root/.local/share/mgs-router-rollbacks/1556468187678117921/` e `/root/.local/share/mgs-router-rollbacks/1556474705412624385/`. Fora do Git; não restaurar estado antigo sobre edições posteriores. Binário pré-bulk não entende flags disabled: não fazer rollback só de código depois de operadores alterarem os estados.

## Falhas intermediárias recuperadas

Pré-produção: CSS terminou em linha vazia e o patch foi reancorado na última linha real; chave de seleção host+newline+path no teste tinha escape literal incompatível e foi corrigida; writer recusou app.js com leitura antiga após patches, então foi feita leitura integral atual antes da edição. Não houve falha de operação produtiva. As duas releases fecharam com QA público completo. O verificador não exige estados ativos nem inventário vazio depois de operações legítimas: deriva expectativas do snapshot autenticado atual, limita o DOM30 e confere todo inventário passando pelas páginas.
