# Financeiro: extratos, aprovações e piloto Nicolas

## Autoridade / precedência
Rodolfo: pedido 1546642267291394199; escopo individual 1546642892427366510; confirmação com Geizian sujeito à aprovação e atividades exclusivas 1546643762686730382; dados da dash 1546645188523331624; piloto só Nicolas 1546645785729572895. Fonte ativa: `/root/mgs-agent/docs/finance-system-product-direction.md`, decisão `FINANCE-PAYMENTS-APPROVALS-NICOLAS-20260907`; relatório `reports/finance-payments-1546642267291394199.md`.

Supersede leitura de despesas somente Rodolfo **no app financeiro**: Geizian tem leitura geral e propostas bloqueadas até aprovação. Não é autorização para outros bots/Discord ou criação automática de pessoas/credenciais. A réplica dos gestores só ocorre após Rodolfo aprovar o piloto Nicolas. Isto não encerra a migração nativa/trial da iniciativa integral.

## Telas / cálculos
- Despesas Gerais; aliases exatos JBF LeadsOn Hub/Tech Bot/Wire Fee → SB; IDs/cobrança original/revisão preservados. Ordenar pelo nome visual em listas e resumos. Remover somente “Despesa da planilha”.
- Movimento Financeiro → Domínios. Total do Site vem imediatamente antes dos países, mês completo e sem influência dos filtros por país/dia.
- `public/financial-summary.js`: origens CAD/USD separadas; campos normalizados USD; ponte de moedas deve fechar com gross do motor. Deduzir inválidos uma vez, revshare = net − gross − invalid; líquido = net + tax + spend + general + staff. ROI NET segue net após rede / custos absolutos − 1. Mensal usa somas, nunca médias de ROI.
- Gastos mensais uniformes no consolidado diário da empresa não viram rateio arbitrário de funcionários por país/site. Total do Site usa somente despesas de site já existentes.

## Modelo de acesso / aprovação
- `finance-ops-schema.sql`, `finance-ops.mjs`, `auth.mjs`, `server.mjs`.
- Rodolfo é owner protegido; parceiros têm leitura/propostas; gestor piloto manager_key é exclusivamente nicolas. Sem defaults permissivos para outra pessoa autenticada.
- Persistir proposta não pode alterar lançamentos. Middleware converte POST de parceiro em 202/pending. Cliente não deve reportar salvo/recalculado.
- Aprovação faz replay do payload **armazenado**, não de body arbitrário enviado no momento da aprovação. `AsyncLocalStorage` + row lock + mesma transação do negócio confirmam a decisão uma vez. Revisão vencida/replay falha sem nova escrita financeira.
- Password/salt/token/credential são proibidos em propostas. Criação de usuário começa desativada; somente owner define senha/ativa, com hash scrypt, revogação de sessões e audit sem segredo. Credenciais de produção vêm do 1Password; não gerar acessos reais por conveniência de teste.
- Atividade/audit global e legado são owner-only. Validar API negada, não só menu escondido. Histórico registra autenticação, alterações, propostas e decisões; não confundir com gravação de cada clique.

## Piloto Nicolas — dados da própria dash
- `/operations?view=manager` é prévia administrativa para Rodolfo. Seu nome continua no cabeçalho porque não existe impersonação. Um login manager tem menu restrito e APIs globais negadas.
- `manager-view.mjs` devolve apenas resultados do namespace Nicolas calculados no DB da dash, seus resumos e sua remuneração. Nunca filtrar o domínio compartilhado inteiro por simples vínculo de gestor.
- **O grafo de dependências não inclui todos os cabeçalhos.** Não descobrir layout presumindo textos em source_cells. `manager-layout.json` contém somente metadados dos oito blocos do snapshot auditado, sem números financeiros; valores vêm de `scenario.result.results`. Nenhum Google Sheets request alimenta a tela.
- Workspaces preservam IDs canônicos do grafo; competência é definida pelo cenário, não por renomear destrutivamente keys Agosto 2026.
- Tabelas largas ficam em scroller interno. Medir `documentElement.scrollWidth`, não concluir overflow geral pela imagem de uma coluna parcialmente visível. No móvel, indicar “deslize”; distinguir prévia owner de sessão manager.

## Extrato / pagamentos
- `finance_ledger`: BRL, centavos, original preservado; kind payment tem direction −1; adjustment explícito +1/−1. Datas reais, não futuras; descrição obrigatória. O estorno preserva a linha e o motivo no audit.
- Devido Geizian = 50% do líquido após despesas/pessoal/mídia, convertido pelo próprio motor; demais remunerações usam os valores calculados existentes, não comissão digitada.
- Saldo = anterior + devido + ajustes − pagamentos. Carregar saldo da competência anterior, não a referência legada de setembro para julho.
- Abertura autorizada agosto: 71 centavos; G129 raw 0.7133221368276281 fica na evidência. H105:H110 sem valores não geram movimentos. “ok” legado sem data/valor de pagamento não vira quitação fictícia.
- Pagamentos/reembolsos não são novamente despesas gerais. Não há integração de transferência bancária. Registros pagos são fixos; devido e saldo acompanham a base enquanto provisória.
- Input date nativo pode continuar MM/DD mesmo com UI PT-BR. Exibir data selecionada por extenso para impedir ambiguidade no registro financeiro.

## Notificações protegidas
- `deploy/finance-notices.mjs`: apenas id/autor/data da proposta saem do DB; ack guarda ID Discord com readback.
- `finance-notifications.py`, no Zeus, lê somente o token Zeus protegido; nunca transporta token para RunCloud/browser. Verifica bot, envia nonce idempotente e faz GET do exato post.
- `meta-lookup-worker.py` existente atende a notificação e a consulta BM, com falhas separadas. Uma notificação por ciclo, timeouts limitados; fallback é aviso interno. Bloquear entrega após cinco falhas, investigar/escalar; não derrubar Meta por falha Discord.
- Destino aprovado: thread 1545426987756298340, Rodolfo 344196393512075265. REPORT-INFRA continua separado em alerts-infra, embed canônico silencioso.

## Validação / recuperação
- Testes: `tests/finance-ops.test.mjs`, `tests/financial-summary.test.mjs`, `tests/payments-pg.mjs`, `tests/payments-browser.mjs`; `tests/run-payments-public.py` usa credencial existente protegida via stdin.
- VM fixtures precisam carregar financial-summary.js antes do app e informar period. Não remover invariantes antigas para esconder regressão.
- `deploy/payments-release.py` é one-shot desta autorização: backup duplo/hash, restore isolado, tabelas aditivas vazias e comparação dos cenários. Não rerodar prepare/publish concluídos como workflow genérico.
- Parar socket **e** serviço da dash durante troca multiarquivo para impedir reativação automática em bundle parcial. Não reiniciar gateway Hermes.
- Reset de testes (`tests/reset-payments-stage.mjs`) verifica nome exato do DB isolado; produção é conexão SELECT-only. Nunca DROP/TRUNCATE/restore vivo para resolver teste.
- `deploy/payments-ui-polish.py` aplicou apenas refinamento móvel/transport bounds, com backup duplo e hash/replace atômico.
- Aceitação publicada: 34 Node, 40 Python, 17 competências, 44 despesas até 43px, oito blocos Nicolas, 10 negações API manager, aprovar/rejeitar/replay/estorno/carry, 390/1440px e zero JS errors. Novos usuários e pagamentos reais: zero. Meta lookup público preservado; contagem de contas BM é variável, não hardcode.
- Evidência em `private/payments-1546642267291394199`; backup remoto `/home/zeus/mgs-finance-backups/1546642267291394199`; stage/DB retidos e inventariados. Rollback de código preserva tabelas/dados novos; rollback de DB requer seu próprio gate. Worker anterior em `meta-worker-before.py` protegido.
