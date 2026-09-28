# Finance — ordem e valores de origem das despesas da empresa

## Autorização e escopo ativo
Rodolfo1547239702464045076 pediu conferência e alinhamento no Dash; entendimento confirmado em1547240897752604704, com correção: manter os nomes atuais do Dash, incluindo SB em lugar de JBF. Thread1545426987756298340.

- Agosto2026 usa valores originais de preenchimento e moedas da própria aba Agosto2026 da planilha principal16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak, gid1736877861.
- Setembro2026 usa valores originais e moedas da aba correspondente, gid1898773018.
- Outubro2026 a dezembro2027 recebem os mesmos valores de origem/moedas de setembro2026, sem copiar cotações nem valores já convertidos.
- Agosto2026 a dezembro2027 usam a ordem das despesas da planilha/prints, não ordem alfabética. Nomes/IDs atuais do Dash permanecem, inclusive SB LeadsOn Hub, SB Tech Bot e SB Wire Fee.
- Cada mês mantém suas próprias cotações, regras de conversão, edições não relacionadas, dados de sites/gastos/receitas, registros de conferência e pessoal. Não copiar estados de pagamento/conferência para meses futuros. Não escrever na planilha.
- Importância da origem: input/edit_amount + mode/edit_currency, jamais usd/brl calculado. CAD e UNITS preservam divisores mensais próprios. Linha vazia não é despesa nova; mapeamentos ambíguos bloqueiam a escrita.

## Crédito/estorno SPYFLIX — decisão ativa1553049180434604103

Rodolfo autorizou que Despesas Gerais distingam `debit` de `credit`. Crédito/estorno existe somente em `category=company`, usa valor de origem positivo e aumenta o resultado; as demais categorias permanecem débito. A UI deve mostrar sinal `+`, saldo líquido e o tipo no editor; a API preserva o tipo em edição, conferência, componentes e auditoria.

Em agosto2026, `company|122` foi substituído — não duplicado — pelo crédito BRL2522, descrição `Crédito/estorno SPYFLIX — 26 lançamentos indevidos`, conferido em2026-09-25. Ele corrige26 lançamentos indevidos de BRL97 e representa BRL1261 antes das regras dependentes, após divisão de50%. A antiga despesa de agosto BRL97 deixou de operar. Setembro2026 em diante continua arquivado pela decisão1553050044813283478.

O cálculo integral da Dash é encadeado: ao trocar a linha de -BRL97 para +BRL2522, Despesas Gerais melhorou BRL2619, a remuneração automática dependente aumentou BRL74,20 e o indicador final de metade aumentou BRL1272,40. Portanto, validar separadamente o valor bruto do crédito e o efeito líquido após remunerações; não prometer que metade do crédito bruto será idêntica à variação final do sócio quando houver fórmulas dependentes.

Produção: revisão547→548, audit2277, release `spyflix-credit-1553049180434604103`; gates208Node+165Python, backup PostgreSQL verificado e readback autenticado por API/UI. Evidência: `reports/finance-spyflix-credit-1553049180434604103.md`.

## Pushalert — decisão ativa1553059046360350835

Rodolfo definiu `pushalert:` (`company|135`) em99 USD por mês desde setembro2026, supersedendo117.24 USD somente nesse ID/vigência. Aplicado e validado nas16competências setembro2026–dezembro2027; agosto preservado, sem criar data de cobrança ou copiar conferência. Novas competências devem manter99 USD, não restaurar o seed anterior. Cotações mensais e demais despesas preservadas, totais recalculados. Fonte/prova: `reports/finance-pushalert-1553059046360350835.md`.

## Cobranças por data e novas exclusões — decisão ativa1553040522287784077

Rodolfo confirmou o desenho em1553040522287784077; acrescentou a exclusão de Ferramenta ver artigos em1553050044813283478.
- A legenda `Despesa extra` deixa de aparecer abaixo do nome na listagem. Supersede somente a preservação visual dessa legenda nas decisões históricas abaixo; origem, valores e remuneração automática permanecem.
- Desde setembro2026, criar/editar Despesas Gerais permite múltiplas cobranças, cada uma com data e valor, botão + e remoção individual. O total fica em uma única linha mensal; reabrir conserva o detalhamento. Moeda única por despesa, conversão mensal existente preservada. Datas de cobrança são separadas de `checked_on` e limitadas ao mês selecionado. Agosto mantém editor de valor único.
- Valores já existentes não recebem data inventada: aparecem como componente legado sem data; novas cobranças exigem data real. Status/data de conferência não são criados nem copiados automaticamente.
- Desde agosto2026, arquivar Wire fee FB (`company|128`), uptimerobot (`company|130`), pagcorp (`company|132`), sendgrid (`company|134`) e ubbersuggest seo (`company|125`), retirando-os da lista ativa e do cálculo.
- Desde setembro2026, arquivar Ferramenta ver artigos (`company|122`), preservando agosto.
- Aplicado às17competências cadastradas até dezembro2027, com backup PostgreSQL verificado/restaurado, recovery por revisão e audit por competência. No cadastro de novas competências, preservar as vigências acima; não ressuscitar essas despesas a partir do seed histórico nem copiar datas de cobranças/conferência.
- Produção verificada por API autenticada e UI desktop/mobile;370testes (208Node+162Python);209cenários anteriores fora do escopo preservados. Edições concorrentes de Rodolfo em agosto foram preservadas.
- Evidência: `reports/finance-expense-charges-1553040522287784077.md`.

## Supersessão das despesas — Rodolfo1553021450158342275 e1553029057153728553

- De agosto2026 em diante, retirar da lista ativa e do cálculo `Topveiw AI dif de cobranca:` (`company|109`), `wordfence premium plugin:` (`company|131`) e `SB LeadsOn Hub:` (`company|141`). Exclusão nativa por arquivamento, sem apagar histórico.
- `SB Wire Fee:` (`company|143`) passa de25 para40 CAD de agosto2026 em diante. Preservar a despesa separada `SB Wire Fee usd:` criada por Rodolfo; não confundir moedas/IDs.
- `Adspower membro extra:` (`company|119`) retirado desde setembro2026. Agosto não foi modificado por Zeus nessa linha; o arquivamento que Rodolfo já fez foi preservado.
- Aplicado e lido de volta em todas as17competências existentes agosto2026–dezembro2027. Audits2196–2212, uma transação por mês, recovery bloqueado e backup restaurado em base isolada. Preservados demais lançamentos/edições de Rodolfo, receitas, gastos, cotações, sites e conferências. Essas regras supersedem as origens históricas somente nos IDs/períodos citados.
- A legenda `Despesa extra` indica cadastro nativo pela dashboard (`extra=true`), em contraste com linhas importadas da planilha. Não é uma cobrança adicional nem duplica valor. A pergunta1553021574402015365 foi respondida como explicação; nenhuma alteração visual foi autorizada ou realizada.
- Prova: `reports/finance-wavesbee-expenses-1553019425706217652.md`;34leituras autenticadas desktop/mobile, zero erros JavaScript.

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
