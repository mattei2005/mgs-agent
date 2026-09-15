# Automação diária de receita GAM por e-mail

## Autoridade e estado

- Autorização: Rodolfo `1547983130038767755`, thread `1545426987756298340`.
- Caixa corporativa: `gm-reports@matteiservicesinc.com`.
- Acesso: IMAP TLS `mail.matteiservicesinc.com:993`, somente leitura com `BODY.PEEK`; credencial permanece no 1Password.
- Remetentes aceitos por endereço exato: `admanager-noreply@google.com` para a entrega diária direta do Google Ad Manager e `contato@marketingdigitalad.com` para encaminhamentos manuais de recuperação. O nome visual “Google Ad Manager” não é usado como prova de identidade.
- Janela: todos os dias entre 08:00 e 08:30, horário Eastern.
- Agendamento físico: intake às `08:03`, `08:08`, `08:18` e `08:28` Eastern. O primeiro par completo executa imediatamente a sequência receita-analisada → gastos → receita-aplicada. O slot de gastos `09:03` e os finalizadores `09:22`, `09:31` e `09:41` permanecem somente como recuperação. A auditoria global de oito dias passou sem colisão operacional; `08:22` foi retirado porque o watchdog Hermes autorizado passou a coincidir nesse minuto.
- Política de partição confirmada, autoridade Rodolfo `1549047147465281658`: uma dúvida de classificação não bloqueia mais as demais linhas. Após os gastos cobrirem a mesma data, as linhas integralmente mapeadas são aplicadas com backup, revisão e readback; somente a partição incerta fica pendente e nunca é tratada como zero. O cutoff do Realizado permanece no dia anterior até a soma aplicada + pendente reconciliar integralmente a fonte e a exceção ser resolvida. Sucesso rotineiro é silencioso no Discord; a thread recebe somente a pergunta exata de confirmação ou um bloqueio técnico persistente após retry automático.
- Estado atual: coletor, parser, runner remoto, sequência direta e fallbacks ativos. A primeira importação, referente a `2026-09-10`, foi reclassificada pela correção de Rodolfo `1548113083774541935`. O ciclo de `2026-09-11` foi concluído sob `1548317688051277918`: 2.480 linhas → 60 grupos, gastos e receita alinhados, Boostingecon `g002-d`/`us-cc-en`, cutoff `2026-09-11`, replay idempotente e states sem falhas. Para 12/09, Rodolfo `1548716825418928213` tornou permanentes Cliquet principal BR → `br-car-br`/`g002-d` e a separação PortalRelevante: domínio principal US → `us-cc-en`/`g001-d`; subdomínio `finanzas.portalrelevante.com` US → `us-cc-es`/`g001-d`.
- Primeiro uso da partição, `2026-09-13`: 2.411/2.412 linhas confirmadas foram aplicadas inicialmente, mantendo apenas `pl_digital-trust_mavroa_us` pendente e o cutoff em 12/09. Após Rodolfo `1549069898674606352` confirmar permanentemente `mavroa.com` / `us-shein-es` com fallback sem gestor `g002-s`, o complemento CAD `0.001441427765333875` foi aplicado sob a mesma identidade de fonte. Estado final: 2.412/2.412 linhas → 54 grupos, USD `6236.244543429341095371`, CAD `21482.90109739138468738523`, zero blockers, revisão 195→196, audit 985, recovery completo bloqueado, replay `already_applied`, cutoff `2026-09-13` e próximo dia esperado `2026-09-14`. API e browser público confirmaram Mavroa, ausência do banner parcial, dia 13 no Realizado, desktop/mobile e zero erro JavaScript.
- Mapeamentos permanentes confirmados por Rodolfo `1549411618570633227` para o fechamento de `2026-09-14`: `openzed.com` BR → `br-car-br`; `ducapes.com` US → `us-cc-es`; `finance.ducapes.com` US → `us-cc-en`; `escalatepower.com` US → `us-cc-en`; `wavesbee.com` US → `us-cc-en`. Os aliases observados `ducapes`, `escalatepower` e `wavesbee` apontam para seus domínios principais. Gestor/operação seguem os cadastros existentes: Openzed `g003-d`, Ducapes `g001-d`, Escalatepower `g002-d` e WavesBee `g003-d`, salvo medium canônico explícito da linha. País novo continua fail-closed.
- Fechamento de `2026-09-14` concluído após essa confirmação: 2.515/2.515 linhas, 59 grupos, CAD `22199.26721940790905194672`, USD `5829.129079952078002026`, zero blockers, revisão 244→245, audit financeiro 1085 e cutoff `2026-09-14`. O primeiro preflight bloqueou corretamente porque o runner remoto ainda não aceitava a nova autoridade; Zeus atualizou somente essa allowlist com backup e hash, repetiu o fluxo e obteve apply/verify completos. Replay seguinte retornou `already_applied`. Readback autenticado desktop 1440/mobile 390 confirmou `Base completa até 14/09`, ausência de banner parcial, fatos dos quatro sites, zero overflow e zero erro JavaScript.

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
6. Mapear placement, país, vertical e gestor pelas regras canônicas. País novo, domínio novo, medium ambíguo ou revisão conflitante são isolados na partição pendente; não inventar classificação nem contaminar as linhas confirmadas.
7. Consolidar com `Decimal`, preservando CAD e USD; exigir igualdade exata `total confirmado + total pendente = total da fonte` em cada moeda.
8. No primeiro intake que congelar um plano válido, chamar imediatamente o sincronizador Meta/Google para a data exata do relatório.
9. Exigir `finance-media-spend-state.last_until` e `media-spend-YYYY-MM.result.summary.until` cobrindo a mesma data; se a sequência não concluir, usar `09:03` e `09:22/09:31/09:41` apenas como fallbacks.
10. Repetir o cálculo produtivo sem escrita, criar `pg_dump` validado e cópia local de mesmo hash, e congelar recovery da revisão corrente dentro da transação.
11. Aplicar por revision guard com IDs determinísticos. Se houver exceção, gravar somente os grupos confirmados e manter o cutoff anterior; após a decisão, completar o mesmo import por identidade e avançar o cutoff somente quando receita integral e gastos do mesmo dia estiverem completos.
12. Ler novamente PostgreSQL e o resultado calculado. Reexecução do mesmo par deve ser no-op; fonte revisada para data já importada bloqueia.
13. Não notificar sucesso rotineiro. Quando houver classificação pendente, notificar esta thread uma vez em mensagem normal e compacta: numerar cada exceção, explicar em uma frase o que foi identificado e o que falta, e fazer uma pergunta compartilhada sobre o mapeamento e sua permanência. Não repetir blocos `Fato/Diagnóstico/Lacuna/Recomendação/Pergunta` por item. Confirmar que o restante já foi aplicado. Bloqueio técnico persistente continua sendo reportado após investigação/retry. Zeus permanece responsável por aplicar somente a decisão autorizada e validar o complemento e o cutoff.
14. Quando o par chegou depois do último slot ou um falso negativo já foi corrigido, `--manual-intake` executa imediatamente a mesma cadeia intake → gastos → receita. Ele ignora somente o relógio do cron; remetente, anexos, data, mapeamento, backup, revision guard e readback permanecem obrigatórios.

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
2. `gamezonead.com`, source placement MX → destino `BR`, vertical `br-game-br`; qualquer medium histórico do domínio é forçado para `g002-s`. Rodolfo `1548133712795795506` confirmou que nenhum gestor opera o site e que o `g001-s` veio de uma UTM configurada incorretamente no início.
3. Fora da exceção GameZoneAd, medium válido `g001`–`g006` com `-s/-d` sempre vence, inclusive quando um gestor roda no site de outro. Quando o medium não identifica um gestor, a linha retorna ao gestor responsável pelo site e mantém a operação: ChatPion `-d`, tráfego direto `-s`. Somente `fincgriffin.com`, `creditoparaveiculo.com` e `yolokfx.com` retornam para MGS/G002; Openzed retorna para Isliago, preservando linhas válidas de Ícaro. Operação mista sem identificação inequívoca bloqueia antes da escrita.
4. Boostingecon pode receber receita orgânica residual quando fora de operação. `pl_digital-trust_boostingecon_us` é Boostingecon / US / `us-cc-en`, sempre `g002-d`; o site não participa do rateio das Despesas Gerais desde setembro/2026. Autoridade: Rodolfo `1548317688051277918`.
5. Cliquet principal em BR é permanentemente `br-car-br` e usa o fallback existente MGS/bot `g002-d` quando o medium não identifica gestor. PortalRelevante principal em US é `us-cc-en` e retorna a Ícaro/bot `g001-d`; somente o subdomínio `finanzas.portalrelevante.com` em US é `us-cc-es`, também Ícaro/bot. O token de placement `portalrelevante` é alias do domínio principal; `portalrelevantefinanzas` é alias do subdomínio. Autoridade: Rodolfo `1548716825418928213`.

Produção final corrigida e validada: 3.058/3.058 linhas → 58 grupos; totais CAD `28042.38632477471319015898` e USD `6303.6497353978632530296` preservados; revisão 138→139; cutoff mantido em 10/09; audit financeiro 686 e confirmação de regra 693; recovery bloqueado `recovery-gam-reclassify-2026-09-10-0c26d8afe327`; repetição no-op em revisão 139. GameZoneAd ficou integralmente em `g002-s`, USD `584.6281651473980147396`. A seção Contas de Anúncio exibe a regra e os responsáveis de setembro/2026 a dezembro/2027. `autolendpro.com` foi confirmado como domínio MGS. Relatório Diário e Cadastro de Domínios têm 44/44 sites iguais em todas as 16 competências. Browser owner/partner desktop/mobile passou sem overflow e sem erro JavaScript.
