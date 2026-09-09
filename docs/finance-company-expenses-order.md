# Finance — ordem e valores de origem das despesas da empresa

## Autorização e escopo ativo
Rodolfo1547239702464045076 pediu conferência e alinhamento no Dash; entendimento confirmado em1547240897752604704, com correção: manter os nomes atuais do Dash, incluindo SB em lugar de JBF. Thread1545426987756298340.

- Agosto2026 usa valores originais de preenchimento e moedas da própria aba Agosto2026 da planilha principal16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak, gid1736877861.
- Setembro2026 usa valores originais e moedas da aba correspondente, gid1898773018.
- Outubro2026 a dezembro2027 recebem os mesmos valores de origem/moedas de setembro2026, sem copiar cotações nem valores já convertidos.
- Agosto2026 a dezembro2027 usam a ordem das despesas da planilha/prints, não ordem alfabética. Nomes/IDs atuais do Dash permanecem, inclusive SB LeadsOn Hub, SB Tech Bot e SB Wire Fee.
- Cada mês mantém suas próprias cotações, regras de conversão, edições não relacionadas, dados de sites/gastos/receitas, registros de conferência e pessoal. Não copiar estados de pagamento/conferência para meses futuros. Não escrever na planilha.
- Importância da origem: input/edit_amount + mode/edit_currency, jamais usd/brl calculado. CAD e UNITS preservam divisores mensais próprios. Linha vazia não é despesa nova; mapeamentos ambíguos bloqueiam a escrita.

## Estado de execução
Concluído e validado em produção em2026-09-09, sob autorização1547240897752604704:
- 17competências,44despesas por competência:748leituras por ID e origem validadas. Nenhuma duplicação.
- Agosto:0alterações financeiras; preservado exatamente. Setembro e outros15meses:42registros existentes preenchidos por mês, incluindo zeros explícitos. Cadastro, identidade, status, conferência e arquivo preservados.
- UI pública:34combinações mês/tela (1440px e390px), ordem na lista e no resumo, nomes SB e ausência de erros JS/overflow validados. Hash do app público igual ao publicado.
- Conversões USD/BRL/CAD/UNITS usam os divisores próprios de cada mês. Teste isolado com USD/BRL6 e USD/CAD1,5 provou recálculo sem mudança da origem; nenhuma cotação live foi alterada.
- Reexecução de verificação:0alterações pendentes.88checks protegidos (incluindo agosto, históricos, ledger e usuários) preservados; os16meses modificados mantiveram overrides/FX, fatos diários e todas as entradas fora de despesas-company.
- Sem escrita em Sheets, restart, alteração de rotina de mídia, pagamento, credencial ou autorização.

## Particularidades preservadas
- SMS Funnel de agosto: origem existente USD4099.78, sem novo arbitramento cambial. A planilha também tem BRL20000 digitado separadamente; permanece como evidência da fonte, conforme aceite histórico de manter F17 (Rodolfo1545866872048717967). Não forçar equivalência à cotação provisória nem substituir silenciosamente a origem.
- SMS Funnel de setembro e meses seguintes: origem BRL30000; não copiar USD calculado.
- Artigos: quantidade R106=0, com derivação P106; mantido o zero existente, sem inferir preço/quantidade não preenchidos. SB Tech Bot preserva UNITS; SB Wire Fee preserva CAD. SB LeadsOn Hub continua sem valor-base quando a célula de origem está vazia.

## Correção visual posterior —1547250519414935592
Rodolfo pediu retirar a legenda “Valor ajustado na dash”. Remoção somente visual nas linhas de despesas; valores, ordem, nomes SB, moedas, cotações e histórico de edição permanecem. As explicações distintas de remuneração automática e despesa extra não foram removidas. Evidências em `apps/finance-system/private/remove-adjusted-label-1547250519414935592/`.

## Evidências e recuperação
Diretório protegido: `/root/mgs-agent/apps/finance-system/private/company-expenses-1547240897752604704/`.
- Fonte: `2026-08-sheet.json`, `2026-09-sheet.json`, `sheet-manifest.json`, `plan.json`, `initial-comparison.json`.
- Backups: `backup-data.dump` e `backup-code.tar.gz`; cópia independente em `/home/zeus/mgs-finance-backups/1547240897752604704-company-expenses/` no host do Dash. Hashes comparados e restore exato testado antes do canário.
- Validações: `stage-apply.json`, `stage-verify.json`, `stage-fx-test.json`, `live-verify.json`, `invariants.json`, `browser-2026-08-17.json`, `published.json`.
- Código: `company-expense-basis-cli.mjs`; orquestração `deploy/company-expense-basis-release.py`; testes `tests/expense-sort.test.mjs`, `tests/company-expense-public.mjs` e `tests/test_expense_origin.py`.
- Rollback deve ser por revisão/ID a partir do backup, preservando alterações concorrentes posteriores; não restaurar o banco inteiro sobre produção automaticamente. Restore de validação retido em `mgs_finance_expenses_1547240897752604704`, com código isolado em `/var/tmp/mgs-finance-expenses-1547240897752604704`, sem servidor auxiliar ativo. Retenção de evidência/backup; exclusão requer confirmação aplicável.
