# Salvamento financeiro mais rápido — 1552071425156845749

Autoridade: Rodolfo1552071425156845749, thread1545426987756298340. Escopo aceito: não recalcular ao mudar somente a confirmação sem mudar valor/modo; reduzir trabalho repetido no recálculo; manter gravação, cálculo e readback reais antes de sucesso. Não alterar taxas, regras financeiras, permissões, credenciais ou fontes.

## Diagnóstico e mudança publicada

O modal aguardava cálculo integral, transação e recarga. A medição inicial do cálculo isolado em produção foi16,447s em agosto/14,218s em setembro, com mais de51mil fórmulas. Perfilamento posterior identificou parsing repetido de coordenadas/referências e varredura do mesmo conjunto de células por bloco de rede como CPU evitável. Instrumentação de profiling adiciona custo e não foi usada para calcular o ganho.

1. `workspace.mjs` deriva internamente `rateConfirmationOnly` somente quando modo anterior e novo são fixed, valor validado é idêntico ao input armazenado e ao resultado calculado. Sem prova, modo diferente ou valor diferente → recálculo completo. Flag enviada pelo cliente não é aceita como atalho.
2. `server.mjs` preserva exatamente overrides/result no caso de confirmação, sem puxar cotações alheias. Ainda executa validação de edição/período/revisão, transação, incremento, auditoria e readback antes da resposta. Retorna `recalculated` para a UI.
3. `public/app.js` continua aguardando a resposta e a revisão nova antes de fechar; informa corretamente confirmação salva ou resultados recalculados, sem simular sucesso antecipado.
4. `calc.py` usa caches limitados somente para coordenadas imutáveis; referências ficam restritas ao Workbook, sem reutilizar resultados/quotes entre requisições. Retorna Ref novo para impedir alteração por referência. Constrói o identificador apenas quando não há valor no cache interno já existente do cálculo.
5. `networks.py` determina a última linha do mês uma vez, em vez de repetir a mesma varredura para cada bloco. Substituições, ordem e regras permanecem idênticas.

## Evidência

Artefatos: `apps/finance-system/private/save-perf-1552071425156845749/`.

- RED real em `red-python.log` e `red-node.log` antes da correção. Regressores adicionados aos testes existentes `tests/test_calc.py` e `tests/workspace.test.mjs`.
- Gates completos:353testes aprovados,197Node +156Python, zero skips/falhas. Manifestos correspondem ao candidato publicado.
- `parity-result.json`: quatro comparações do resultado completo, agosto/setembro com taxas originais e com imposto alterado apenas no replay isolado. JSON inteiro igual, não somente totais. Zero escrita financeira produtiva.
- `stage-result.json`: interface real em stage com snapshots reais; confirmação completa1937ms desktop e2096ms mobile. Resultado/overrides preservados, revisão incrementada. Alteração numérica do imposto executou cálculo real. Requisição deliberadamente retida manteve botão desabilitado/modal aberto; concorrência da mesma revisão retornou200/409. Zero erro JS.
- `remote-benchmark.json`: mesmo host/snapshot, processos isolados antes/depois. Agosto13087→9198ms, redução30%; setembro12760→8645ms, redução32%; paridade integral em ambos. Nenhuma gravação financeira/remota de arquivos neste benchmark.
- `published.json`: controlador coordenado committed, backups/hash/readback válidos, reinícios somente app financeira remota e worker financeiro local. Todos os hashes de cenários/revisões/inputs/resultados iguais na janela da publicação. Zero mutação financeira.
- `production-readback.json`: código efetivamente publicado calculou agosto9691ms/setembro8814ms, zero erro. PostgreSQL, app e socket active.
- `browser-production.json`:34 combinações competência/viewport, zero erro JS, zero POST financeiro; replay de rateio parcial, cinco APIs de gestores, conferência e redirecionamento anônimo preservados. Sessão de validação encerrada.

Confirmação (~2s) foi medida em stage isolado, não por mudança artificial de status em produção. O tempo9s é de cálculo produtivo, não promessa do clique inteiro: mudanças numéricas ainda aguardam commit/reload. Ganho observado não é SLA.

## Preservação e rollback

Backup PG completo com catálogo/sha256 e cópia local em `backup.json`/`before.dump`. Remoto: `/home/zeus/mgs-finance-backups/save-perf-1552071425156845749/before.dump`. Arquivos originais em `before/` e journal exato `private/releases/save-performance-1552071425156845749/`. Candidato, banco isolado de stage e provas ficam preservados para auditoria; sem limpeza destrutiva.

A publicação não alterou valores financeiros, taxa5,08 de agosto, fórmulas-fonte, histórico, agenda ou credenciais. Os testes de status/imposto usaram somente banco isolado. Rollback é dos arquivos listados no manifesto, seguido de reinício financeiro/readback; nunca restaurar banco produtivo para desfazer uma otimização de código.

## Continuidade

Procedimento salvo em `mgs-finance-dashboard`v0.1.70, `references/current-security-performance-and-dr.md`: prova restrita de confirmação, caches sem estado financeiro, paridade completa, tempos comparáveis e espera por sucesso real. Registry, checkpoint, inventário e REPORT-INFRA vinculados à autorização desta tarefa.
