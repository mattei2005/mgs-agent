# Sincronização março–agosto2026 — planilha geral e dashboard

Pedido: Rodolfo `1555094707556585526`; confirmação adicional dos saldos acumulados: `1555098371448905801`; thread `1545426987756298340`. Correções de origem consultadas na thread `1555012688915075152`.

## Resultado financeiro aplicado e verificado

- Captura independente de36abas: planilha principal e cinco planilhas de gestores, março–agosto2026, via Service Account canônica; zero erros de fórmula.
- Março–julho:30documentos históricos atualizados pelo fluxo owner de refresh da própria competência; novas versões imutáveis e ponteiros mensais, sem sobrescrever os40registros originais de finance_history.
- Readback autenticado:303.091células dos30documentos exatamente iguais às capturas frescas usadas pelo worker. Dashboard, diário, despesas, câmbios e visões dos cinco gestores consultam essas versões.
-42registros de remuneração de gestores revisados nas seis competências, preservando cinco ocorrências em branco na fonte. Agosto mantém os valores nativos pagáveis iguais em centavos às linhas da planilha; Gustavo sem valor não foi transformado em cobrança.
- Os25registros de finance_ledger permaneceram exatamente iguais, inclusive IDs/datas/valores/exclusões. Nenhum pagamento, estorno, cobrança ou compensação foi criado. A dispensa dos pequenos acertos discutida na thread de origem não virou novo lançamento.
- Janeiro/fevereiro e seus ponteiros preservados. Receitas, despesas, cadastros e regras de setembro em diante não foram substituídos pela planilha incompleta de setembro; somente o saldo anterior acompanha o histórico corrigido, como confirmado.

### Totais líquidos da empresa, USD

- Março:99.402,43
- Abril:111.293,53
- Maio:84.168,06
- Junho:65.023,63
- Julho:29.983,23
- Agosto:28.913,35

### Saldos Geizian, BRL

- Julho: anterior na dash−1.090,05 → fonte corrigida3.217,61.
- Agosto: anterior−532,57 →3.775,09.
- Ponte de carry:+4.307,66, sem rededuzir os pagamentos existentes. Em agosto: abertura321761centavos +devido7387362 +movimento−7331614 =saldo377509.

## Delimitação honesta de agosto nativo

O workspace nativo de agosto foi preservado integralmente: fonte AdOps/GAM já reconciliada, taxas e12linhas de pessoal. O lucro mensal final e todas as remunerações pagáveis conferem em centavos com a planilha atual. A diferença raw do lucro é somente Sheet−Dash=−0.00041352251939943878233USD.

Os resultados individuais de gestores usam a precisão nativa das receitas e dos custos, enquanto a planilha tem outras precisões intermediárias. Diferenças Sheet−Dash em USD:

- Joe:−0.0010984745085
- Nicolas:+0.003733451122
- Isliago:+0.001693238615
- Kelly:−0.002279503720
- Ícaro:−0.004021094879

Apesar de todas estarem abaixo de meio centavo USD, Nicolas e Ícaro atravessam uma fronteira de arredondamento e exibem diferença de0,01USD em seu resultado. Os BRL pagáveis permanecem iguais. Isto é uma ressalva de paridade intermediária, não remuneração pendente. Não foram criadas receitas, despesas ou ajustes artificiais para forçar resultados intermediários bit-idênticos. Não declarar igualdade absoluta de cada célula de agosto.

O artefato preliminar `august-manager-cell-diff.json` compara o grafo legado, cujas células podem ser substituídas por fatos nativos, e **não representa a tela real**. Sua interpretação foi supersedida por `august-manager-actual-diff.json`, produzido pelo managerView efetivo, e pelo readback público. Não usar as diferenças grandes do grafo legado como nova anomalia.

## Backup, ensaio e execução

- Dump PostgreSQL custom212188781bytes, SHA256 `38585d722e495f214064a41cafe677d9c7d2a04c2ef90b269da8cf27a8de529f`.
- Cópias: `apps/finance-system/private/sheet-sync-1555094707556585526/pre-sync.dump` e `/home/zeus/mgs-finance-backups/gam-email/sheet-sync-1555098371448905801/data.dump` no host financeiro; hashes iguais e catálogo validado.
- Restore materializado `mgs_finance_sync_1555098371448905801`:40históricos,25ledger,283cenários originais. Aplicação de30documentos, repetição idempotente e retorno do ponteiro anterior testados; pagamento de agosto retornou exatamente ao estado anterior no ensaio de rollback.
- A primeira conexão do stage como mgsfinance foi corretamente negada pelo pg_hba. Nenhuma permissão/configuração foi relaxada: o ensaio usou mgs_pg no banco isolado e uma cópia privada do runtime em `/var/lib/mgs-postgresql18/stage-sheet-sync-1555098371448905801`.
- Publicação pelo endpoint existente `/api/history-refreshes`, owner real, cinco requests rastreados em `refresh-requests.json`. Autoridade funcional do fluxo1547732274936553532, execução atual1555094707556585526/1555098371448905801. AuditIDs2665–2669 confirmam os cinco imports.
-156verificações de navegador público: seis meses, desktop/mobile, sete áreas gerais, cinco prévias de gestor e Pagamentos; zero erro JS/POST financeiro no readback. Na primeira tentativa, o menu móvel estava recolhido; o harness foi corrigido para abri-lo, sem alterar a aplicação.

## Falha de recibo de julho — recuperada e prevenção publicada

A fonte de julho já corrigiu SB Tech Bot para CAD via `N140 = SUM(Q140/$H$1)*-1`,629,28CAD. O helper antigo devolvia `source_already_cad` sem o objeto de comprovação exigido pelo transporte da fila. O banco foi atualizado corretamente, mas o recibo ready de julho falhou; a conclusão em lote deixou também recibos posteriores pendentes.

A recuperação primeiro provou todos os30documentos no banco e confirmou a fórmula CAD ao vivo no Google; só então concluiu os recibos pendentes, sem reimport financeiro cego. Worker recuperado para ok/pending0.

Correção permanente em `history_policy.py`:
- reconhecer a fórmula CAD já correta antes de recalcular o grafo;
- validar629,28, taxa positiva e conversão exata;
- preservar células/hash/valores e devolver a prova CAD necessária à fila;
- manter intacto o caminho de correção quando a origem ainda usar GBP.

RED/GREEN, ensaio com seis documentos reais e transporte da fila, gates completos226Node +180Python =406testes PASS. Publicação coordenada `history-cad-proof-1555098371448905801`, apenas helper/teste locais; recarregou só o worker financeiro, não gateway nem serviço de aplicação.

Canário público posterior `d2436569-7abe-4607-bfd1-64a3326acb75`:ready,changed=false,6documentos,células/fechamento idênticos, prova source_already_cad relida,73,06s. PostgreSQL, serviço financeiro, socket e worker ativos; nenhuma falha operacional pendente.

## Evidências e continuidade

Workspace privado: `apps/finance-system/private/sheet-sync-1555094707556585526/`.
Fontes principais: `verification.json`, `browser-production.json`, `refresh-public-readback.json`, `stage-proof.json`, `backup-stage.json`, `carry-impact.json`, `dashboard-before.json`, `dashboard-after.json`, `august-manager-actual-diff.json`, `july-canary-proof.json`, `july-canary-queue-readback.json`, `code-manifest.json` e `candidate/private/gates/`.

Backups, restore e runtime de stage preservados; nenhuma exclusão autorizada nesta tarefa. Journal de código: `apps/finance-system/private/releases/history-cad-proof-1555098371448905801/`.
Checkpoint: `ZEUS-FINANCE-SHEET-SYNC-MAR-AUG-1555094707556585526`.
