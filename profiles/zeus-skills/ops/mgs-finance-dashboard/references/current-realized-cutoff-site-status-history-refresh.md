# Realizado por cutoff, status de sites e atualização histórica

## Autoridade e escopo

Autoridade: Rodolfo `1547727478011727963`, correção `1547731247793709056`, confirmação final `1547732274936553532` e instrução de encerramento `1547775936697737288`, thread `1545426987756298340`.

Esta regra vale para agosto de 2026, setembro de 2026 e as competências seguintes. Janeiro–julho permanecem meses fechados e só podem ser atualizados a partir da própria aba mensal pelo fluxo explícito descrito abaixo.

## Pagamentos

- Renderizar, imediatamente após o título, uma faixa compacta somente com `USD → BRL`, `USD/CAD` e `GBP → USD`, no padrão visual da Dashboard.
- Informar `Fechado` ou `Provisório` e a captura/fonte quando houver.
- Não mostrar inválidos em Pagamentos. Eles permanecem nos cálculos e nas áreas próprias; não apagar taxas nem valores.
- O valor devido de mês aberto usa `domain.realized.half_brl`, não o fechamento mensal que inclui obrigações futuras.
- Gestores continuam sem acesso a indicadores gerais da empresa.

## Dashboard — cards de resultado

- Correção Rodolfo `1547790708344234056`: os dois cards superiores devem mostrar 100% da empresa, nunca 50%.
- `Líquido realizado · 100%` usa `domain.realized.profit` e sua conversão BRL.
- `Estimativa do mês · 100%` usa duas vezes a projeção interna de 50%, mantendo a mesma fórmula de cutoff/despesas.
- A mudança é somente nos dois cards superiores. A linha de participação de 50% na composição e os pagamentos de Geizian continuam em 50%; não alterar sociedade, ledger ou remuneração por causa desta apresentação.

## Cutoff operacional

- Persistir uma única adição `kind=data_cutoff` por competência; não inferir pelo último valor diferente de zero.
- Agosto/2026 foi fechado em `2026-08-31`; setembro/2026 foi confirmado até `2026-09-09`; meses futuros começam com `date=null` até a carga integral ser validada.
- `domain.realized` inclui fatos somente até o cutoff e apropria Despesas Gerais e funcionários proporcionalmente aos dias completos.
- Dias posteriores ficam zerados na visão realizada, sem esconder nem apagar os fatos armazenados.
- A estimativa mensal projeta somente o resultado operacional acumulado até o cutoff e soma as Despesas Gerais e funcionários mensais exatamente uma vez: `operacional_acumulado / dias_completos × dias_do_mês + despesas_mensais`.
- Ranking atual usa fatos realizados e apenas a parcela apropriada das despesas do site. Mês histórico continua usando o `LUCRO:` original.

## Sites e gestores

- Mostrar todos os sites em uma tabela única com coluna `Ativo/Inativo`.
- Legenda: Ativo entra nos resultados e participa do rateio das Despesas Gerais; Inativo entra nos resultados, mas não participa do rateio.
- Receita e gastos de sites inativos nunca são removidos dos totais gerais.
- Desde setembro/2026: Cephyric, Escalatepower e Mavroa são `MGS/G002 · Inativo`; suas receitas originais CAD permanecem intactas. O recálculo inicial produziu apenas sub-centavos de USD por reaplicação do câmbio CAD, auditados como bridge, sem perda de receita original.
- Em site compartilhado, exibir somente os gestores com receita realizada no período. `SEM_COMISSAO`/G002 aparece como MGS. Para Yolokfx em setembro: MGS, Ícaro, Isliago, Joe, Kelly e Nicolas.

## Atualização de mês fechado

- O botão de owner lê novamente apenas a competência selecionada nas seis planilhas aplicáveis, via Service Account canônica e sem escrita no Google Sheets.
- Publicação cria versões históricas imutáveis e move atomicamente somente os ponteiros daquele mês; `finance_history` original permanece intacta.
- Julho deve preservar a decisão canônica posterior de SB Tech Bot `629,28 CAD`, mesmo que a fórmula live da aba use I1/GBP. O refresh aplica o overlay autorizado `1547697182948458611`, registra a correção no documento e nunca reintroduz a moeda errada.
- A fila genérica aceita apenas `account_id` numérico. Refresh histórico deve transportar `account_id=YYYYMM`, `platform=history`, `period` e `actor`; a conclusão exige `captured_at`, 5/6 documentos, booleano `changed` e correção CAD em julho.
- Falha de coleta preserva a versão anterior e retorna erro; não repetir cegamente. Cache parcial de julho sem o overlay CAD é inválido e deve ser recapturado.

## Validação e evidência

- Testes finais: 112/112 Node e 74/74 Python.
- Produção: 24/24 competências com faixa de câmbios; owner desktop/mobile; Nicolas sem indicadores gerais; zero erros JavaScript.
- Botão real de julho: fonte já atualizada, 6 documentos, `changed=false`, correção CAD preservada; julho devido BRL 71.984,76526680421 e saldo BRL −1.090,0485236818408.
- Setembro é provisório e pode variar com câmbio/fontes. O readback público final confirmou cutoff `09/09`, despesas futuras ausentes e a fórmula de estimativa exata.
- Artefatos: `/root/mgs-agent/work/finance-current-policy-1547732274936553532/` e `/root/mgs-agent/apps/finance-system/private/current-policy-1547732274936553532/`.
- Backup remoto: `/home/zeus/mgs-finance-backups/1547732274936553532/`.
