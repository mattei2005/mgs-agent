# Automação diária de receita GAM por e-mail

## Autoridade e estado

- Autorização: Rodolfo `1547983130038767755`, thread `1545426987756298340`.
- Caixa corporativa: `gm-reports@matteiservicesinc.com`.
- Acesso: IMAP TLS `mail.matteiservicesinc.com:993`, somente leitura com `BODY.PEEK`; credencial permanece no 1Password.
- Remetente aceito: `contato@marketingdigitalad.com`.
- Janela: todos os dias entre 08:00 e 08:30, horário Eastern.
- Agendamento físico: `08:03`, `08:13`, `08:22` e `08:28` Eastern. O inventário global de oito dias confirmou zero colisões com jobs operacionais; as sobreposições restantes são apenas baselines densas e usam locks distintos.
- Estado atual: coletor, parser, runner remoto e cron ativos; primeira importação, referente a `2026-09-10`, bloqueada antes de escrita por três decisões empresariais descritas abaixo.

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
8. Repetir o cálculo produtivo sem escrita, criar `pg_dump` validado e cópia local de mesmo hash, e congelar recovery da revisão corrente dentro da transação.
9. Aplicar por revision guard com IDs determinísticos; atualizar o cutoff apenas para o próximo dia completo.
10. Ler novamente PostgreSQL e o resultado calculado. Reexecução do mesmo par deve ser no-op; fonte revisada para data já importada bloqueia.
11. Notificar esta thread uma vez por sucesso ou por decisão/bloqueio acionável.

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

Leitura real: 3.058 linhas; CAD `28042.38632477471319015898`; USD `6303.6497353978632530296`. A simulação remota completa passou com 59 grupos e zero escrita, usando somente hipóteses isoladas para provar o runner. Elas não são regras ativas.

A produção permanece bloqueada até Rodolfo decidir:

1. `finanzas.topfeed.fun`, placement ES, CAD `11.78005180558166382`: confirmar vertical, proposta `es-cc-es`.
2. `gamezonead.com`, placement MX, USD `0.0371801394250000036`: confirmar vertical e tratamento, proposta `mx-game-es` com `g002-s`, preservando MX.
3. `yolokfx.com`, uma linha CAD `1.3080415466602981` sem `utm_medium`, campanha também ausente: confirmar o gestor, proposta `g002-s` como resíduo.

Nenhuma receita de 10/09 foi aplicada e o cutoff continua em 09/09 até essas três respostas.
