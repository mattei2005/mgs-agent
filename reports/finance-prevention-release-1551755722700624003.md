# Primeiro pacote preventivo financeiro — publicado

Autoridade: Rodolfo `1551755722700624003`, thread `1545426987756298340`.
Fonte do escopo: auditoria `reports/finance-prevention-audit-1551747394356518933.md`, seção “Recomendação de execução”: handler/readback pós-falha, regressão obrigatória e primeira entrega de conferência/rastreabilidade. Decisão: execução em etapas, preservando lançamentos, cálculos aprovados e centavos explicados. O pedido não autoriza pagamentos, fixação de câmbio, alterações de permissão, credenciais, systemd ou migração integral do motor.

## Entrega publicada

- URL: https://dash.mgsdigitalcorp.com/review.html?period=2026-09
- Menu de Rodolfo: **Conferência mensal**. Somente consulta, agosto/2026–dezembro/2027. Perfis de sócio/gestores não recebem a nova visão global; permissões existentes e logins não foram alterados.
- Roteiro de fechamento com distinção entre consistência interna, comprovantes externos e liquidação. Sem botão que finja fechar/liquidar o mês por calendário.
- Conferência de receita, inválidos, receita após share, impostos, mídia, despesas gerais, folha, resultado, participação de 50%, cinco visões de gestores, competência e ausência de movimentos herdados nos meses futuros.
- Folha e saldos reutilizam os resultados e a mesma função de Pagamentos, inclusive créditos ativos e exclusões históricas. Não há segundo motor de remuneração/saldos.
- A consulta reúne um snapshot PostgreSQL **REPEATABLE READ, READ ONLY**, revisão e hash. Paginação de origens rejeita revisão diferente com HTTP409, evitando misturar cotações/snapshots silenciosamente.
- Origem por site/dia/gestor: moedas originais separadas de USD convertido, células, componentes e linhas de fonte quando armazenados, tag do lançamento, hash do lote, ajustes de atribuição, decisões/supersessões e histórico com autor/data. A tag já classificada de GAM não é rotulada como medium bruto recebido. Informação não registrada aparece como tal, sem inferência de autorização.
- Ajustes mensais preservam `date=YYYY-MM`; não são falsamente atribuídos ao dia31. Linhas legadas sem receita preenchida não viram receita zero; a recomposição soma receitas informadas/nativas e mantém os gastos das linhas com somente mídia. A cobertura é explicada separadamente, sem declarar conciliação externa a partir de uma soma interna.
- Precisão dos controles: comparação decimal de18casas, limite exclusivo de truncamento por número de parcelas. Não existe tolerância universal de R$0,01; teste de parcela ausente de0,01 e de0,00000001 reprova. Valores e fórmulas originais ficam intactos.

## Recuperação GAM

- `gam_recovery.py` e `gam-recovery-inspect.mjs`: intervenção marcada na primeira falha; leitura/transportes têm um retry limitado. Credenciais, cobrança, autoridade e invariantes não recebem reparo automático.
- Depois de apply/verify incerto, primeiro reler cenário, lote, auditoria e recovery em uma transação somente leitura. Se já aplicado e validado, retomar apenas a leitura. Repetição de apply somente após ausência comprovada, erro transitório e no máximo uma tentativa adicional. Estado parcial/conflitante/desconhecido bloqueia escrita.
- Removida afirmação incondicional “A dashboard não foi alterada” no handler técnico. Ausência comprovada do lote de receita não é confundida com ausência de gastos já processados.
- Falhas são registradas desde a primeira; cinco execuções consecutivas falhas bloqueiam a continuação automática. Rotina saudável permanece silenciosa. Contrato operacional local atualizado; horários/crons e regras financeiras não foram modificados.
- Readback do lote real20/09: `inspect` retornou `applied`, audit1629, mesmos hashes do runner, zero escrita financeira. Falhas de conexão/commit foram injetadas somente nos testes, não na produção.

## Gate obrigatório

- Comando: `npm run test:release`. Fases separadas para execução foreground controlada: `python3 release_gate.py --phase node` e `--phase python`.
- Fixture real privada de agosto, revisão456, com SHA256 e proveniência verificados. Arquivo em `private/release-fixtures/`, Git-ignored, nunca servido como asset público.
- Gate rejeita fixture ausente/alterada, teste falho, cancelado, TODO ou pulado, e alteração de código durante a validação. A publicação desta tarefa exige manifestos Node/Python compatíveis com os bytes atuais.
- Casos reais de agosto incluem quatro parcelas Openzed/G001-D, Yolokfx MGS, receita nativa única, resumo dos cinco gestores e CPV16/Nicolas. Matriz complementar cobre pares CAD/USD, mês/futuro, folha, ledger edit/delete, reimportação idempotente e recuperação pós-falha.
- Resultado final: **174 Node +121 Python =295 testes aprovados, zero skips**. Auditoria de dependências: zero vulnerabilidades reportadas.

## Validação real

- Backup PostgreSQL custom, catálogo validado, cópia local com hash idêntico; restauração materializada no banco isolado `mgs_finance_prevention_1551755722700624003`.
- API de stage:17competências; zero divergências internas. Agosto e setembro:17controles cada; competências futuras:18cada. Isolamento de papéis, cinco gestores, revisão obsoleta409 e créditos Geizian R$899,60 validados. Nenhum SQL financeiro mutável executado pelos testes.
- Traces auditados e deduplicados:2.092movimentos de agosto;1.485de setembro. As quatro reatribuições Openzed têm oito registros bidirecionais (origem/destino), não oito transferências.
- Browser stage e produção:17competências, desktop1440px e celular390px, abertura dos detalhes/decisões de Openzed, navegação pelo menu, zero erros JS, zero POSTs financeiros. O stage usa snapshots reais do banco restaurado e leituras autenticadas da produção; o teste final usa os endpoints publicados de fato.
- Publicação: hashes dos10arquivos remotos conferidos; cenários/revisões/overrides/additions/resultados, ledger e contagem de auditoria financeira idênticos imediatamente antes/depois do cutover sob locks. PostgreSQL, serviço e socket ativos.
- Cache protegido:5leituras sequenciais +20concorrentes do workspace com25hits e payload byte-idêntico na revisão490. Cinco consultas concorrentes à nova conferência passaram. APIs continuam no-store/CSP/HSTS; sem login401; origem direta403.
- Nenhuma escrita em Sheets, lançamento, pagamento, crédito, atribuição, câmbio, regra de remuneração ou arredondamento foi executada nesta entrega. Login/logout geraram somente auditoria técnica normal.

## Incidente durante o ensaio — resolvido e comunicado na entrega

Uma consulta de fingerprint criada nesta tarefa agregava **documentos JSON completos** do banco restaurado. Embora o banco fosse separado, o serviço PostgreSQL/cgroup era compartilhado. A consulta ultrapassou o limite de3GiB e disparou OOM; o PostgreSQL produtivo foi reiniciado automaticamente pelo systemd. Logs:2026-09-22 01:16:11UTC OOM;01:16:17UTC novamente pronto. Não foi restart do gateway Hermes nem alteração de limite/serviço feita por Zeus.

Correção: hash por documento/linha antes de agregar apenas os hashes curtos; removida a consulta ilimitada do harness. Ensaios repetidos passaram. Serviços, consulta PostgreSQL, login e APIs/browser públicos validados depois da recuperação. Comparação de170cenários contra o backup pré-incidente confirmou os mesmos estados, lançamentos e inputs não cambiais; as três cotações automáticas foram separadas explicitamente. O fingerprint exato pré/pós-deploy também permaneceu idêntico. Readback final: `NRestarts=1`, memória PG512741376bytes, limite3221225472bytes, ativo; sem nova reincidência nos ensaios e testes concorrentes subsequentes.

Falhas locais de harness adicionais, corrigidas antes da entrega: contagem dos quatro ajustes Openzed ignorava a representação bidirecional; fixture sintética de inspect omitia campos obrigatórios; APIRequestContext exigia `expires` no storageState de cookies. Não foram defeitos financeiros nem validações ignoradas. Casos RED test-first para módulos ausentes foram esperados. A lição de isolamento de recursos/hash limitado foi persistida na skill de segurança/performance.

## Backups, rollback e resíduos preservados

- Workspace: `apps/finance-system/private/prevention-release-1551755722700624003/`.
- Manifesto de backup: `backup.json`; código remoto anterior: `code-before.tar.gz`; originais locais: `before/` e `contract-before.json`.
- Stage: `/var/tmp/mgs-finance-prevention-1551755722700624003`; banco restaurado acima. Permanecem parados/inertes, sem servidor de testes persistente; preservados para rollback/evidência. Não houve DROP ou limpeza destrutiva.
- Rollback é limitado aos arquivos desta entrega; restaurar o conjunto remoto pelo helper privado e o runner/contrato local correspondente, validar hashes e reiniciar somente o serviço financeiro. Nunca restaurar um dump sobre produção para reverter apenas interface/código. Novos arquivos sem referência podem permanecer inertes, sem deletar por inferência.

## Limites e próximo passo

Esta é a **primeira entrega consultiva do fechamento**, não o fechamento nativo integral. Importação de comprovantes, aprovação versionada do owner, congelamento/reabertura mensal e reconstrução de metadados antigos ausentes não são declarados concluídos. Câmbios provisórios e diferenças de precisão aceitas em agosto foram preservados.

Próximo pacote recomendado: catálogo de regras com vigência e prévia de abertura do mês (permanente × exceção mensal × pendência), associado às confirmações/documentos do fechamento. Depois, substituir adaptadores da planilha gradualmente, sempre com paridade. Esse restante não foi executado nem tratado como autorizado por esta mensagem.

## Evidência

`published.json`, `db-before-publish.json`, `db-after-publish.json`, `stage-result.json`, `browser-stage.json`, `browser-production.json`, `gate/{node,python}-result.json`, `gate-negative-tests.json`, `gam-live-readback.json`, `public-performance.json`, `security-probes.json`, `stage-failure-diagnosis.json`, `incident-recovery-validation.json`, `backup.json`. Nenhum subagente/background iniciado neste turno.
