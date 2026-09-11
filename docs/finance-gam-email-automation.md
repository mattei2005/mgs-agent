# Automação diária de receita GAM por e-mail

## Autoridade e estado

- Autorização: Rodolfo `1547983130038767755`, thread `1545426987756298340`.
- Caixa corporativa: `gm-reports@matteiservicesinc.com`.
- Acesso: IMAP TLS `mail.matteiservicesinc.com:993`, somente leitura com `BODY.PEEK`; credencial permanece no 1Password.
- Remetente aceito: `contato@marketingdigitalad.com`.
- Janela: todos os dias entre 08:00 e 08:30, horário Eastern.
- Agendamento físico: intake read-only às `08:03`, `08:13`, `08:22` e `08:28`; gastos às `09:03`; finalização da receita às `09:22`, `09:31` e `09:41` Eastern. O inventário global de oito dias confirmou zero colisões com jobs operacionais; as sobreposições restantes são apenas baselines densas e usam locks distintos.
- Estado atual: coletor, parser, runner remoto e os dois crons ativos. A primeira importação, referente a `2026-09-10`, foi aplicada e validada após as decisões de Rodolfo `1548001704119762945`. A auditoria `1548008533608636527` separou intake de finalização e adicionou gates de gasto em state + PostgreSQL, impedindo que o cutoff exponha receita antes do gasto do mesmo dia.

## Fontes obrigatórias

O par diário é completo somente com:

1. Rede2/USD: assunto `Report: Report Digital Trust (adx 2) ...`, anexo `Report Digital Trust (adx 2).xlsx`, rede `All Digital Marketing`.
2. Rede1/CAD: assunto `Relatório: Digital Trust ...`, anexo `Digital Trust.xlsx`, rede `00-JBF Digital Server`.

A data vem das linhas do arquivo e deve coincidir nos dois relatórios. Assunto, horário do e-mail e nome repetido do anexo não definem a data financeira. Falta de uma fonte nunca vira receita zero.

## Pipeline ativo

1. Entrar por IMAP read-only e manter as mensagens não lidas.
2. Filtrar remetente + família exata de assunto.
3. Validar nome, MIME, duas abas, cabeçalhos, moeda, rede, timezone `America/Sao_Paulo` e uma única data nas linhas.
4. Preservar cada anexo com SHA-256 e deduplicar por `Message-ID + hash`.
5. Exigir o par da mesma data e ordem diária sem lacunas.
6. Mapear placement, país, vertical e gestor pelas regras canônicas. País novo, domínio novo, medium ambíguo ou revisão conflitante bloqueiam antes de produção e geram pergunta na thread.
7. Consolidar com `Decimal`, preservando CAD e USD; exigir igualdade integral dos totais de origem.
8. Durante 08:00–08:30, somente congelar o plano validado; nunca importar receita nem avançar cutoff.
9. Após a rotina de gastos das 09:03, exigir `finance-media-spend-state.last_until` e `media-spend-YYYY-MM.result.summary.until` cobrindo a mesma data; tentar finalização às 09:22/09:31/09:41.
10. Repetir o cálculo produtivo sem escrita, criar `pg_dump` validado e cópia local de mesmo hash, e congelar recovery da revisão corrente dentro da transação.
11. Aplicar por revision guard com IDs determinísticos; atualizar o cutoff somente quando receita e gastos do mesmo dia estiverem completos.
12. Ler novamente PostgreSQL e o resultado calculado. Reexecução do mesmo par deve ser no-op; fonte revisada para data já importada bloqueia.
13. Notificar esta thread uma vez por sucesso ou por decisão/bloqueio acionável.

## Artefatos

- Orquestrador: `apps/finance-system/finance_gam_revenue_sync.py`
- Parser: `apps/finance-system/gam_revenue.py`
- Runner: `apps/finance-system/gam-revenue-core.mjs`, `apps/finance-system/gam-revenue-cli.mjs`
- Regras: `data/finance-gam-revenue-rules.json`
- Contrato: `data/finance-gam-revenue-contract.json`
- Estado: `data/finance-gam-revenue-state.json`
- Evidência/bootstrap: `apps/finance-system/private/gam-automation-1547983130038767755/`
- Runs imutáveis: `apps/finance-system/private/gam-email-runs/`
- Log: `logs/finance-gam-revenue.log`

## Primeiro par — 10/09/2026

Leitura real: 3.058 linhas; CAD `28042.38632477471319015898`; USD `6303.6497353978632530296`. Após Rodolfo `1548001704119762945`, as regras efetivas ficaram:

1. `finanzas.topfeed.fun`, source placement ES → destino `US`, vertical `us-cc-es`; gestor válido da fonte preservado.
2. `gamezonead.com`, source placement MX → destino `BR`, vertical `br-game-br`, gestor `g002-s`.
3. Desde 10/09/2026, qualquer linha com `utm_medium` realmente ausente (`-`/vazio), em qualquer site, vai para `g002-s`. Medium válido `g001`–`g006` com `-s/-d` continua preservado; valor não vazio porém não canônico permanece sujeito à regra específica do site ou bloqueio.

Produção aplicada e validada: 3.058/3.058 linhas → 74 grupos; revisão 122→123; cutoff 09/09→10/09; audit 593; recovery bloqueado `recovery-gam-email-2026-09-10-84ae1d403bb3`; backup remoto e cópia local 49.720.742 bytes com SHA-256 idêntico; repetição no-op em revisão 123. Readback público owner desktop/mobile: 31 linhas diárias, TopFeed Finanzas/GameZoneAd/Yolokfx visíveis e zero erro JavaScript.
