# Financeiro: extratos, aprovações e piloto Nicolas

**Current-state supersession:** piloto Nicolas-only e ordem alfabética das despesas são históricos. Os cinco gestores têm acesso conforme `references/manager-access-and-history-dispositions.md`; Despesas Gerais seguem a ordem de origem e moeda da competência em `references/company-expense-source-order.md`. Preservar regras não supersedidas de extrato, propostas, aprovação e edit/delete registradas neste arquivo.

## Autoridade / precedência
Rodolfo: pedido 1546642267291394199; escopo individual 1546642892427366510; confirmação com Geizian sujeito à aprovação e atividades exclusivas 1546643762686730382; dados da dash 1546645188523331624; piloto só Nicolas 1546645785729572895. Fonte ativa: `/root/mgs-agent/docs/finance-system-product-direction.md`, decisão `FINANCE-PAYMENTS-APPROVALS-NICOLAS-20260907`; relatório `reports/finance-payments-1546642267291394199.md`.

Supersede leitura de despesas somente Rodolfo **no app financeiro**: Geizian tem leitura geral e propostas bloqueadas até aprovação. Não é autorização para outros bots/Discord ou criação automática de pessoas/credenciais. A réplica dos gestores só ocorre após Rodolfo aprovar o piloto Nicolas. Isto não encerra a migração nativa/trial da iniciativa integral.

## Telas / cálculos
- Despesas Gerais; aliases exatos JBF LeadsOn Hub/Tech Bot/Wire Fee → SB; IDs/cobrança original/revisão preservados. Ordenar pelo nome visual em listas e resumos. Aplicar trim somente na apresentação/chave de ordenação: ` Server Agent:` vinha com espaço inicial e aparecia incorretamente antes de Adspower. O teste deve ter oráculo independente do texto com padding; comparar uma lista com a mesma ordenação defeituosa dá falso PASS. Preservar nome/ID/valor de origem. Remover somente “Despesa da planilha”.
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
- Tabelas largas ficam em scroller **somente horizontal**; referência `manager-layout-and-total-contrast.md` supersede limite vertical anterior e formato decimal bruto. Mês completo no fluxo da página,31dias em agosto/30em setembro, visão agrupada por país/total; nenhuma coluna eliminada. Medir `documentElement.scrollWidth`, não concluir overflow geral pela imagem de uma coluna parcialmente visível. No móvel, indicar “deslize”; distinguir prévia owner de sessão manager.

## Extrato / pagamentos
- `finance_ledger`: BRL, centavos, original preservado; kind payment tem direction −1; adjustment explícito +1/−1. Datas reais, não futuras; descrição obrigatória. O estorno preserva a linha e o motivo no audit.
- Devido Geizian = 50% do líquido após despesas/pessoal/mídia, convertido pelo próprio motor; demais remunerações usam os valores calculados existentes, não comissão digitada.
- Saldo = anterior + devido + ajustes − pagamentos. Carregar saldo da competência anterior, não a referência legada de setembro para julho.
- Abertura autorizada agosto: 71 centavos; G129 raw 0.7133221368276281 fica na evidência. H105:H110 sem valores não geram movimentos. “ok” legado sem data/valor de pagamento não vira quitação fictícia.
- Pagamentos/reembolsos não são novamente despesas gerais. Não há integração de transferência bancária. Registros pagos são fixos; devido e saldo acompanham a base enquanto provisória.
- Input date nativo pode continuar MM/DD mesmo com UI PT-BR. Exibir data selecionada por extenso para impedir ambiguidade no registro financeiro.

## Pagamentos — pedido de simplificação1551662555783635014

Rodolfo considera confuso manter linhas ESTORNADO misturadas aos lançamentos atuais e pediu ações **Editar** e **Excluir** por item, também nas opções do lançamento. A confirmação/continuação `1551700964975714437` exige recurso geral de Pagamentos em agosto e todos os meses posteriores, sem replicação manual mensal. **Implantado e relido** em produção: relatório `reports/finance-payments-edit-delete-1551700964975714437.md`. Supersede a preparação anterior e a interface orientada a Estornar: originais excluídos ficam fora da lista e do saldo; o histórico auditável permanece. As seis linhas anuladas de Geizian foram retiradas somente da exibição, sem apagar banco/audit; os cinco créditos ativos899.60 foram preservados. Não tratar esta implantação como autorização para exclusão física ou pagamento bancário.

### Contrato reutilizável de Editar/Excluir

- Usar `ledger-edit.mjs` e rotas `/api/finance/ledger/:id/edit|delete` para todas as competências nativas. Não codificar agosto/setembro no componente ou copiar valores de agosto para meses futuros. Janeiro–julho fechado continua somente leitura.
- Enviar competência e beneficiário **do lançamento**, não do seletor atual. A API mantém registros anteriores para calcular o saldo; a apresentação acumulada anterior foi supersedida pelo filtro mensal autorizado em1555055743785373760 abaixo. Exigir confirmação, versão/fingerprint sob row lock e campos permitidos; validar natureza, centavos exatos e data real não futura. Guardar before/after no audit na mesma transação. O fingerprint não é credencial nem substitui autorização.
- Preservar owner→escrita, partner→proposta pendente/owner→aprovação atômica, manager→leitura própria. Testar recusa de revisão vencida, replay, item já excluído, escopo divergente e payload adulterado na aprovação.
- Frontend filtra `voided_at` somente da lista, nunca elimina audit. Renderizar Editar por linha e Opções→Editar/Excluir; verificar por GET o ID exato após gravação e não informar sucesso para proposta ainda pendente.
- Exercitar mutações somente em restore PostgreSQL isolado, com mesmas grants; produção recebe validação autenticada somente leitura, abertura/cancelamento dos diálogos e fingerprint financeiro antes/depois. Cobrir todos os períodos disponíveis, desktop/mobile e carregamento de saldo entre competências.
- Para stage sob `mgs_pg`, copiar o binário Node privado para o diretório do stage e validar versão/hash, em vez de abrir permissões do home `mgsfinance` quando o caminho do runtime não for atravessável.

## Filtro mensal do extrato — Rodolfo1555055743785373760

A autorização supersede somente a apresentação acumulada da lista de Pagamentos, não o cálculo de saldo, o ledger, os meses fechados ou as permissões. **Publicado e relido**: `reports/finance-payments-month-1555055743785373760.md`; checkpoint `ZEUS-FINANCE-PAYMENTS-MONTH-1555055743785373760`. Aceitação:402testes,1054checksstage,442checkspúblicos,13beneficiários ×17meses ×2larguras;11IDs tinham movimentos antigos indevidamente repetidos e2sem movimentos não evidenciavam o defeito. Cenários e ledger preservados, zero writes financeiros.

- Filtrar linhas visíveis por `entry.period === response.period` e `!entry.voided_at`, para todos os beneficiários e perfis. A competência é **Referência**, não a data do pagamento: um lançamento datado de setembro cuja referência é agosto aparece em agosto.
- Preservar a consulta cumulativa da API e o saldo anterior, devido, movimento e saldo final. Filtrar a consulta para apenas o mês antes do cálculo apagaria a memória de saldo; a correção é de apresentação.
- Em mês sem itens próprios, exibir `Nenhum lançamento neste mês.`; nunca repetir os antigos nem criar um lançamento zero. Informar que os itens anteriores continuam no saldo anterior.
- Validar todos os IDs retornados pelo seletor de cada competência, inclusive funções distintas da mesma pessoa e beneficiários sem itens. Uma lista vazia não demonstra ausência do defeito: testar a lógica comum com fixture isolada e comparar o baseline quando existirem movimentos.
- Reproduzir o defeito antes da correção; testar todos os meses nativos, desktop/mobile, owner/partner/manager, referência versus data, itens anulados, botões e cartões iguais à API. Manter o acesso do gestor limitado aos seus próprios beneficiários. Janeiro–julho usa outra apresentação histórica somente leitura, preservada.
- Produção só recebe código com gates completos, stage real do renderer e fingerprint de cenários **e ledger** antes/depois sob admissão exclusiva. Nunca registrar pagamento ou editar saldo para demonstrar o filtro.

### Complemento: virada mensal e dados antigos após erro — Rodolfo1555083506529468438

- O motor Decimal pode emitir zero como `0E-30`/`0E-40`. A conversão para centavos deve aceitar notação decimal científica finita, preservando dígitos, arredondamento half-up e limites por inteiro/BigInt; nunca usar `Number(value)*100` como reparo nem converter valores inválidos em zero. Os inputs manuais continuam com sua validação monetária estrita.
- Validar a virada de cada mês em `America/New_York`. Visitar meses futuros não exercita o cálculo que passa a ocorrer quando aquele mês se torna atual: o defeito de outubro ficou mascarado pelo ramo de devido futuro zero antes da meia-noite. Reproduzir a API e a transição completa, não apenas o filtro de linhas.
- Ao trocar a competência de Pagamentos, limpar imediatamente os cartões/linhas/ações anteriores e mostrar carregamento. Falha deixa estado nulo, aviso do mês solicitado e retry explícito; nunca manter uma tabela válida do mês anterior sob um seletor diferente. Sucesso do retry remove a mensagem de erro anterior.
- Descartar respostas e erros de requests ultrapassados por uma seleção posterior; validar competência/beneficiário da resposta antes de renderizar. Testar resposta atrasada, erro após carga válida, recuperação e ausência de ações enquanto dados estão indisponíveis.
- Comparar todos os payloads que já funcionavam antes/depois e os centavos contra um oráculo independente Python Decimal. Ensaios de API usam consultas reais capturadas somente leitura; cenários e ledger produtivos permanecem intocados. Estado desta correção pertence ao checkpoint `ZEUS-FINANCE-PAYMENTS-ROLLOVER-1555083506529468438`, não à simples presença desta regra.

## Correção autorizada de créditos existentes

- Solicitação e confirmação adicional do Critical Subset são distintas: confirmar beneficiário, competência, valores finais, sinal e itens a anular antes da escrita. A confirmação `1551658668393631755` autorizou apenas os créditos Geizian agosto preparados em `1551652370998624328`, não redistribuição Openzed ou pagamento bancário.
- Quando não há edição no ledger, preservar originais com estorno auditado e criar substitutos positivos somente para os valores alterados. Anular sem substituto apenas os itens removidos expressamente confirmados; preservar registros já corretos. Não duplicar créditos nem marcar pagamento/Conferido como atalho.
- Fazer snapshot exato local/remoto, ensaio transacional com rollback validado, aplicação atômica com locks e guarda de estado esperado, audit com autoridade/IDs substituídos, segundo apply no-op e readback autenticado da mesma tela. Comparar cenários e outros beneficiários antes/depois.
- O diretório remoto `/home/zeus/mgs-finance-backups` pode pertencer a root. Inspecionar ownership antes do mkdir e usar o subdiretório canônico já gravável pelo executor (atualmente `gam-email`, zeus0700), sem mudar permissões do pai. Hash local/remoto deve coincidir.
- Caso validado: `reports/finance-geizian-credits-1551658668393631755.md`, audit1708: quatro créditos substituídos, dois anulados sem substituto, renovação60 preservada, cinco ativos somando899.60; zero pagamentos. Isto supersede o estado histórico de seis créditos0.01, não constitui regra de valor para outros meses.

## Notificações protegidas
- `deploy/finance-notices.mjs`: apenas id/autor/data da proposta saem do DB; ack guarda ID Discord com readback.
- `finance-notifications.py`, no Zeus, lê somente o token Zeus protegido; nunca transporta token para RunCloud/browser. Verifica bot, envia nonce idempotente e faz GET do exato post.
- `meta-lookup-worker.py` existente atende a notificação e a consulta BM, com falhas separadas. Uma notificação por ciclo, timeouts limitados; fallback é aviso interno. Bloquear entrega após cinco falhas, investigar/escalar; não derrubar Meta por falha Discord.
- Destino aprovado: thread 1545426987756298340, Rodolfo 344196393512075265. REPORT-INFRA continua separado em alerts-infra, embed canônico silencioso.

- Rodolfo `1548118855958798437` requested a Geizian login with exactly Dashboard, Relatório Diário, Gestores, Despesas Gerais, Despesas Funcionários, Câmbio e Inválidos, and Pagamentos. The `partner` menu/API boundary is active with those seven areas; Cadastro de Domínios, Contas de Anúncio, Aprovações, Usuários and Histórico remain unavailable. Rodolfo confirmed the critical credential operation in `1548133712795795506` after saving the password in the exact 1Password item. Production readback: `geizian`, `geizianpereira@gmail.com`, `+55 87 9918-2658`, partner, enabled, revision 1; real login, allowed/denied APIs and desktop/mobile menus passed without exposing the secret.

## Validação e recuperação
- Testes: `tests/finance-ops.test.mjs`, `tests/financial-summary.test.mjs`, `tests/payments-pg.mjs`, `tests/payments-browser.mjs`; `tests/run-payments-public.py` usa credencial existente protegida via stdin.
- VM fixtures precisam carregar financial-summary.js antes do app e informar period. Não remover invariantes antigas para esconder regressão.
- `deploy/payments-release.py` é one-shot desta autorização: backup duplo/hash, restore isolado, tabelas aditivas vazias e comparação dos cenários. Não rerodar prepare/publish concluídos como workflow genérico.
- Parar socket **e** serviço da dash durante troca multiarquivo para impedir reativação automática em bundle parcial. Não reiniciar gateway Hermes.
- Reset de testes (`tests/reset-payments-stage.mjs`) verifica nome exato do DB isolado; produção é conexão SELECT-only. Nunca DROP/TRUNCATE/restore vivo para resolver teste.
- `deploy/payments-ui-polish.py` aplicou apenas refinamento móvel/transport bounds, com backup duplo e hash/replace atômico.
- Aceitação publicada: 35 Node (incluindo regressão de padding/ordenação), 40 Python, 17 competências, 44 despesas até 43px, oito blocos Nicolas, 10 negações API manager, aprovar/rejeitar/replay/estorno/carry, 390/1440px e zero JS errors. Novos usuários e pagamentos reais: zero. Meta lookup público preservado; contagem de contas BM é variável, não hardcode.
- Evidência em `private/payments-1546642267291394199`; backup remoto `/home/zeus/mgs-finance-backups/1546642267291394199`; stage/DB retidos e inventariados. Rollback de código preserva tabelas/dados novos; rollback de DB requer seu próprio gate. Worker anterior em `meta-worker-before.py` protegido.
