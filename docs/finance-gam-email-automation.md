# Automação diária de receita GAM por e-mail

## Autoridade e estado

- Autorização: Rodolfo `1547983130038767755`, thread `1545426987756298340`.
- Caixa corporativa: `gm-reports@matteiservicesinc.com`.
- Acesso: IMAP TLS `mail.matteiservicesinc.com:993`, somente leitura com `BODY.PEEK`; credencial permanece no 1Password.
- Remetente aceito: `contato@marketingdigitalad.com`.
- Janela: todos os dias entre 08:00 e 08:30, horário Eastern.
- Agendamento físico: intake às `08:03`, `08:08`, `08:18` e `08:28` Eastern. O primeiro par completo executa imediatamente a sequência receita-analisada → gastos → receita-aplicada. O slot de gastos `09:03` e os finalizadores `09:22`, `09:31` e `09:41` permanecem somente como recuperação. A auditoria global de oito dias passou sem colisão operacional; `08:22` foi retirado porque o watchdog Hermes autorizado passou a coincidir nesse minuto.
- Estado atual: coletor, parser, runner remoto, sequência direta e fallbacks ativos. A primeira importação, referente a `2026-09-10`, foi reclassificada pela correção de Rodolfo `1548113083774541935`: fonte e totais foram preservados, a atribuição por gestor foi corrigida e o cutoff permaneceu em `2026-09-10`.

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
8. No primeiro intake que congelar um plano válido, chamar imediatamente o sincronizador Meta/Google para a data exata do relatório.
9. Exigir `finance-media-spend-state.last_until` e `media-spend-YYYY-MM.result.summary.until` cobrindo a mesma data; se a sequência não concluir, usar `09:03` e `09:22/09:31/09:41` apenas como fallbacks.
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
2. `gamezonead.com`, source placement MX → destino `BR`, vertical `br-game-br`; medium válido é preservado e linha sem gestor retorna para MGS com a operação `-s`.
3. Medium válido `g001`–`g006` com `-s/-d` sempre vence, inclusive quando um gestor roda no site de outro. Quando o medium não identifica um gestor, a linha retorna ao gestor responsável pelo site e mantém a operação: ChatPion `-d`, tráfego direto `-s`. Somente `fincgriffin.com`, `creditoparaveiculo.com` e `yolokfx.com` retornam para MGS/G002; Openzed retorna para Isliago, preservando linhas válidas de Ícaro. Operação mista sem identificação inequívoca bloqueia antes da escrita.

Produção corrigida e validada: 3.058/3.058 linhas → 59 grupos pela nova atribuição; totais CAD `28042.38632477471319015898` e USD `6303.6497353978632530296` preservados; revisão 137→138; cutoff mantido em 10/09; audit 684; recovery bloqueado `recovery-gam-reclassify-2026-09-10-f9f0460ae26c`; repetição no-op em revisão 138. A seção Contas de Anúncio exibe a regra e os responsáveis de setembro/2026 a dezembro/2027. Relatório Diário e Cadastro de Domínios têm 44/44 sites iguais em todas as 16 competências. Browser owner desktop/mobile passou sem overflow e sem erro JavaScript.
