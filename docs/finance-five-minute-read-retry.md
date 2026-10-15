# Finance — nova tentativa de leitura após cinco minutos

## Decisão e escopo

Autoridade: Rodolfo Mattei, mensagem `1560288130085560351`, thread `1545426987756298340`.

Quando uma consulta de gastos de anúncios falhar de forma potencialmente transitória, fazer automaticamente uma nova tentativa após cinco minutos, sem depender de pedido de Rodolfo. Vale para a leitura de gasto na descoberta de contas e para a consulta/conferência detalhada diária Meta/Google da dashboard financeira. Esta decisão não muda campanhas, budgets, fontes financeiras, atribuição, câmbio ou horários de cron e não cria uma regra universal de replay de escritas externas.

Esta regra supersede, neste escopo, a espera de um segundo da repetição curta descrita sob a autoridade1549047147465281658. A correção/investigação começa na primeira falha; a nova consulta elegível aguarda300segundos. Um resultado divergente de validação é candidato à reconsulta, não prova de que a falha original era transitória.

## Comportamento executável

- Executar as leituras iniciais e preservar as evidências e os resultados válidos.
- Consolidar falhas de descoberta e detalhe em uma única rodada de recuperação; esperar300segundos antes de repetir somente as leituras elegíveis. Uma espera por rodada, não cinco minutos multiplicados pelo número de contas. A janela é contada após o conjunto inicial de leituras, antes da rodada de recuperação; não é um SLA de exatamente cinco minutos após cada erro individual.
- Realizar uma única nova leitura por item que já falhou. Se uma conta recuperada na descoberta tiver gasto positivo, executar também sua primeira consulta detalhada, com todos os gates existentes. Se esse novo detalhe falhar, preservar a pendência, sem outra rodada recursiva no mesmo ciclo.
- Não repetir dados que já foram confirmados nem fabricar zeros. Uma reconsulta não relaxa identidade, moeda, timezone, período, paginação, unicidade diária ou conciliação diário/agregado.
- Repetir somente classes explicitamente admitidas: timeout/falha de transporte, HTTP429/5xx, códigos Meta transitórios/rate-limit conhecidos e falha de validação para reconferência. Erros conhecidos de credencial, permissão, cobrança, conta fechada e erro desconhecido ficam fora da tentativa atrasada; preservar escalonamento apropriado.
- Preservar a parada por cinco falhas consecutivas/scan interrompido, a proteção por locks e admissão de release, a deduplicação e os fallbacks agendados. Nunca criar outro escritor durante a espera.
- A rodada é somente leitura. O importador financeiro permanece responsável por backup, transação, idempotência e readback; receita/SMS continuam na cadeia aprovada. Sucesso é comunicado apenas depois de verificar o fechamento completo; falha persistente continua parcial e segue a política de alerta existente.
- Registrar horário, intervalo, IDs, tentativas e recuperação em `sources/source-retry.json` e nas linhas da coleção, sem credenciais. O estado `waiting` não equivale a resultado financeiro aplicado.

## Continuidade e aceitação

Código: `apps/finance-system/finance_spend_sources.py`.
Testes: `apps/finance-system/tests/test_api_first_reporting.py`.
Checkpoint de publicação: `ZEUS-FINANCE-RETRY-1560288130085560351`.
Evidência: `apps/finance-system/private/retry-five-min-1560288130085560351/`.

A decisão aprovada não é prova de implantação. Exigir gates completos do candidato, teste real de espera300s seguido de GET Meta, manifesto/journal e leitura dos hashes ativos. O ensaio usa a falha real preservada do dia14/10 como entrada de replay e uma nova consulta real; não induz falha em produção, não reimporta valores e não comprova a causa exata do erro histórico.

Manter o orçamento existente do cron standalone900s e da chamada sequencial1200s, compartilhando a única espera300s entre as duas fases; não adicionar uma espera separada de300s por fase/conta. Indisponibilidade extrema ainda pode exceder o orçamento externo e deve permanecer falha explícita, nunca falso sucesso.
