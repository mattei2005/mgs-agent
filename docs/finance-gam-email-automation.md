# Automação diária de receita GAM por e-mail

## Autoridade e estado

- Autorização: Rodolfo `1547983130038767755`, thread `1545426987756298340`.
- Caixa corporativa: `gm-reports@matteiservicesinc.com`.
- Acesso: IMAP TLS `mail.matteiservicesinc.com:993`, somente leitura com `BODY.PEEK`; credencial permanece no 1Password.
- Remetentes aceitos por endereço exato: `admanager-noreply@google.com` para a entrega diária direta do Google Ad Manager e `contato@marketingdigitalad.com` para encaminhamentos manuais de recuperação. O nome visual “Google Ad Manager” não é usado como prova de identidade.
- Janela: todos os dias entre 08:00 e 08:30, horário Eastern.
- Agendamento físico: intake às `08:03`, `08:08`, `08:18` e `08:28` Eastern. O primeiro par completo executa imediatamente a sequência receita-analisada → gastos → receita-aplicada. Assim que o dia financeiro anterior estiver integralmente aplicado, os demais slots agendados do mesmo ciclo viram no-op: não procuram nem alertam pelo par da data corrente, que ainda não venceu. O slot de gastos `09:03` e os finalizadores `09:22`, `09:31` e `09:41` permanecem somente como recuperação. A auditoria global de oito dias passou sem colisão operacional; `08:22` foi retirado porque o watchdog Hermes autorizado passou a coincidir nesse minuto.
- Política de partição confirmada, autoridade Rodolfo `1549047147465281658`: uma dúvida de classificação não bloqueia mais as demais linhas. Após os gastos cobrirem a mesma data, as linhas integralmente mapeadas são aplicadas com backup, revisão e readback; somente a partição incerta fica pendente e nunca é tratada como zero. O cutoff do Realizado permanece no dia anterior até a soma aplicada + pendente reconciliar integralmente a fonte e a exceção ser resolvida. **Supersessão de notificações por Rodolfo1553778586807304213:** ao concluir gastos e receita, enviar uma confirmação conjunta por data financeira nesta thread. Erro ou preenchimento parcial também exige mensagem normal explicando o problema, o que já entrou e a decisão que falta. Sem embeds/cartões/blocos de código. A ausência do par da data corrente, ainda não vencido, permanece sem alerta. A política de partição financeira não mudou.
- Estado atual: coletor, parser, runner remoto, sequência direta e fallbacks ativos. A primeira importação, referente a `2026-09-10`, foi reclassificada pela correção de Rodolfo `1548113083774541935`. O ciclo de `2026-09-11` foi concluído sob `1548317688051277918`: 2.480 linhas → 60 grupos, gastos e receita alinhados, Boostingecon `g002-d`/`us-cc-en`, cutoff `2026-09-11`, replay idempotente e states sem falhas. Para 12/09, Rodolfo `1548716825418928213` tornou permanentes Cliquet principal BR → `br-car-br`/`g002-d` e a separação PortalRelevante: domínio principal US → `us-cc-en`/`g001-d`; subdomínio `finanzas.portalrelevante.com` US → `us-cc-es`/`g001-d`.
- Primeiro uso da partição, `2026-09-13`: 2.411/2.412 linhas confirmadas foram aplicadas inicialmente, mantendo apenas `pl_digital-trust_mavroa_us` pendente e o cutoff em 12/09. Após Rodolfo `1549069898674606352` confirmar permanentemente `mavroa.com` / `us-shein-es` com fallback sem gestor `g002-s`, o complemento CAD `0.001441427765333875` foi aplicado sob a mesma identidade de fonte. Estado final: 2.412/2.412 linhas → 54 grupos, USD `6236.244543429341095371`, CAD `21482.90109739138468738523`, zero blockers, revisão 195→196, audit 985, recovery completo bloqueado, replay `already_applied`, cutoff `2026-09-13` e próximo dia esperado `2026-09-14`. API e browser público confirmaram Mavroa, ausência do banner parcial, dia 13 no Realizado, desktop/mobile e zero erro JavaScript.
- Mapeamentos permanentes confirmados por Rodolfo `1549411618570633227` para o fechamento de `2026-09-14`: `openzed.com` BR → `br-car-br`; `ducapes.com` US → `us-cc-es`; `finance.ducapes.com` US → `us-cc-en`; `escalatepower.com` US → `us-cc-en`; `wavesbee.com` US → `us-cc-en`. Os aliases observados `ducapes`, `escalatepower` e `wavesbee` apontam para seus domínios principais. Gestor/operação seguem os cadastros existentes: Openzed `g003-d`, Ducapes `g001-d`, Escalatepower `g002-d` e WavesBee `g003-d`, salvo medium canônico explícito da linha. País novo continua fail-closed.
- Fechamento de `2026-09-14` concluído após essa confirmação: 2.515/2.515 linhas, 59 grupos, CAD `22199.26721940790905194672`, USD `5829.129079952078002026`, zero blockers, revisão 244→245, audit financeiro 1085 e cutoff `2026-09-14`. O primeiro preflight bloqueou corretamente porque o runner remoto ainda não aceitava a nova autoridade; Zeus atualizou somente essa allowlist com backup e hash, repetiu o fluxo e obteve apply/verify completos. Replay seguinte retornou `already_applied`. Readback autenticado desktop 1440/mobile 390 confirmou `Base completa até 14/09`, ausência de banner parcial, fatos dos quatro sites, zero overflow e zero erro JavaScript.
- Mapeamentos permanentes confirmados por Rodolfo `1550483550027911290` para `2026-09-17` e relatórios futuros: `xyvlov.com` US → `us-cc-en`; placement principal `zuout` → `zuout.com` US / `us-cc-en`; o cadastro canônico já existente `finanzas.zuout.com` permanece separado em US / `us-cc-es`; Zyclor usa o identificador operacional `zyclor`, país DE, vertical `de-cc-de` e fallback MGS/ChatPion `g002-d`. **Decisão final de setembro — Rodolfo `1551316692565499956`:** manter Zuout principal e Finanzas conforme a atribuição existente da fonte: G006/Nicolas e G002/MGS, inclusive antes19/09. Essa decisão supersede o corte19/09 proposto em `1551312942182441111`; não reatribuir retroativamente os seis fatos G006 de15–18/09. Preservar dados e importador de setembro, sem criar regra nova para medium ausente. Agosto e seus destinos aprovados continuam inalterados. O literal não cadastrado `finanzas.zuou.com` não foi criado como domínio nem alias.
- Fechamento de `2026-09-17` concluído após esses mapeamentos: 2.951/2.951 linhas, 60 grupos, CAD `28515.64163834952179049939`, USD `5217.760979330298098511`, zero blockers, revisão final 396, audit financeiro 1418 e cutoff `2026-09-17`. Zyclor foi registrado como site inativo/MGS/SB Rede1 de setembro/2026 a dezembro/2027, sem delta de caixa. Dois preflights falharam de forma segura antes de qualquer escrita financeira — primeiro pela allowlist remota da nova autoridade, depois porque Zyclor ainda não existia no catálogo; ambos foram corrigidos com backup/readback e o replay da fonte retornou `already_applied`.

## Confirmação de 21/09 — Eggbev BR e CarCreditAd

Autoridade: Rodolfo `1551587001629937686`, thread `1545426987756298340`.

- `eggbev.com` / BR → `br-car-br`, permanente. Preservar as regras existentes de gestor; a linha de 20/09 ficou em `g006-d`/Nicolas.
- Placement `carcreditad` → domínio `carcreditad.com` / US / `us-car-en`, responsável MGS/G002, fallback direto `g002-s`, permanente. A possibilidade de origem orgânica foi levantada por Rodolfo, não comprovada; não converter essa hipótese em classificação comprovada de canal.
- O catálogo já continha `CarCreditAd`, ID `site-carcreditad-principal`, SB Rede2, US e INATIVO. Reutilizado sem duplicação; responsável MGS confirmado nas competências setembro/2026–dezembro/2027. Permanece INATIVO/Não participa do rateio; nenhum lançamento de gasto ou ativação de campanha foi criado. Agosto e histórico preservados.
- Fechamento de 20/09: 2.841/2.841 linhas → 59 grupos; CAD `33353.85505568913596904793`, USD `7125.93845096898306093501`; zero pendências. Foram completadas somente as duas parcelas pendentes: Eggbev CAD `0.4732937456451401` e CarCreditAd USD `0.00007200027000000001`.
- Revisão de setembro 465→466 (cadastro MGS)→467 (complemento GAM), audit financeiro 1629, cutoff `2026-09-20`; replay `already_applied`. API autenticada e browser desktop/mobile confirmaram ausência do aviso parcial, ambos os lançamentos e CarCreditAd inativo/MGS. Evidência: `reports/finance-gam-close-1551587001629937686.md`.

## Confirmação DicasFinancas e conclusão de 21/09

Autoridade permanente: Rodolfo `1551947602562392085`, thread `1545426987756298340`.

- `dicasfinancas` → `dicasfinancas.info`, BR, `br-cc-br`. Medium ausente retorna a G002/MGS, preservando o sufixo de operação da regra existente (`s` como default); medium canônico explícito de outro gestor continua prevalecendo.
- O catálogo financeiro não tinha esse site. Criado como `dicasfinancas.info`, ID `site-dicasfinancas-info`, Rede1/CAD, MGS, nas competências setembro/2026–dezembro/2027. Cadastro sem nova participação no rateio (`INATIVO`/Não participa), para preservar as cotas e valores existentes; isso não afirma que o site web ou campanhas estejam inativos.
- Complemento de21/09: CAD `0.018550884640459408`, `g002-s`. Fonte integral:3035 linhas →59 grupos; CAD `28798.31949953348322594333`, USD `6913.927141529553880181`, zero pendências. Revisão setembro518→519, audit1867, cutoff21/09; replay `already_applied` na mesma revisão.
- A correção de apresentação aprovada na mesma mensagem supersede somente os zeros nas linhas parciais: Despesas Gerais e Funcionários devem aparecer rateados também nessas linhas e compor resultado/ROI. O TOTAL REALIZADO continua limitado aos dias completos; dias futuros sem atividade continuam zerados. Não muda os valores mensais nem a política de completude.
- Ativar regras novas somente depois de o catálogo correspondente e o runner estarem prontos. Dois slots concorrentes falharam no preflight durante a atualização:09:31 detectou hash do runner ainda não publicado;09:41 encontrou o site ainda sem cadastro. Nenhum complemento incorreto foi aplicado. Cadastro concluído, fluxo repetido, flags de falha zerados e recuperação validada.
- Evidência: `reports/finance-session-rateio-dicas-1551947602562392085.md`; apply `private/gam-email-runs/20260922T094347-0400/`; replay `private/gam-email-runs/20260922T095141-0400/`.

## Classificações TopFeed BR / FinanceAdx AR e conclusão de 22/09

Autoridade: Rodolfo `1552302899483254856`, thread `1545426987756298340`.

- `finance.topfeed.fun` / BR → `br-car-br`; placement `pl_digital-trust_topfeed_br`. Preservar o domínio FinanceTopFeed, distinto de TopFeed principal e TopFeed Finanzas, e as regras existentes de gestor. O complemento concreto permanece `g004-d`/Joe, CAD `1.185705108781502`.
- `financeadx.com` / AR → `ar-cc-es`; placement `pl_digital-trust_financeadx_ar`. O complemento permanece `g006-d`/Nicolas, CAD `0.0011544944890569291`.
- Mapeamentos registrados nas regras ativas para reutilização; países diferentes continuam bloqueados até classificação comprovada. Nenhuma moeda, rede, proprietário, status ou rateio alterado.
- Fechamento22/09:3018 linhas→59grupos; CAD `33274.61950929689367271061`, USD `6997.6437650657147014774`; zero blockers; revisão568→569, audit1983, cutoff22/09. As57entradas já importadas foram preservadas; somente duas parcelas completaram a fonte. Replay `already_applied`, mesma revisão/audit.
- Código/regras publicados pelo release guard juntamente com o refinamento visual autorizado1552303522287194132.365testes sem skips; browser autenticado confirmou fatos e ausência do dia parcial; outros cenários preservados. Fonte: `reports/finance-gam-layout-1552302899483254856.md`.

## WavesBee principal e Finanzas — decisão1553019425706217652

- `wavesbeefinanzas` / `pl_digital-trust_wavesbeefinanzas_us` → `finanzas.wavesbee.com`, US, `us-cc-es`, responsável Isliago/G003. O domínio principal `wavesbee.com` permanece US / `us-cc-en`, também Isliago/G003. Gestores canônicos explícitos de outras linhas continuam prevalecendo; nenhuma fusão entre os dois domínios.
- Alias, rótulo e vertical registrados nas regras ativas. Criado cadastro financeiro distinto `site-wavesbee-finanzas` / `WavesBee Finanzas`, Rede1/CAD, setembro2026–dezembro2027. Mantido sem participação nova no rateio; principal preservado.
- Fonte24/09 concluída:3000linhas→58grupos, CAD `33673.06509297804855478367`, USD `8104.3400871613600962897`. Apenas complemento CAD `0.012742353809102358`, `g003-d`; zero blockers, revisão678/audit2192, último dia completo24/09. Replay `already_applied`; 57grupos prévios preservados.
- Release `wavesbee-1553019425706217652`:369testes sem skips, ensaio financeiro, catálogo pronto antes das regras, backup/restore e readback. Evidência consolidada: `reports/finance-wavesbee-expenses-1553019425706217652.md`.

## Growpowerhub DE — decisão1554828914424156170

- Rodolfo1554828011700752445 confirmou `de-cc-de` e G002/MGS;1554828914424156170 confirmou domínio `growpowerhub.com` e repetição automática somente do placement `pl_digital-trust_growpowerhub_de`. O sufixo `_de` identifica as tags alemãs desta operação; não inferir geolocalização do visitante nem aplicar `de-cc-de` universalmente a outros sites.
- Regra ativa: alias `growpowerhub` → `growpowerhub.com`; par domínio/DE → `de-cc-de`; responsável G002/MGS. O mesmo placement em novos relatórios não exige nova pergunta. Outro sufixo/país sem regra confirmada continua isolado e exige decisão de Rodolfo, sem herdar DE. Preservar a precedência normal de medium canônico.
- As10linhas originais de29/09 tinham literal `mg01-d`: gestor não canônico retorna a G002, preservando operação explícita `-d`, portanto `g002-d`. A campanha não substitui o sufixo do placement. Tráfego orgânico é apenas hipótese, não atribuição comprovada.
- Site cadastrado como `site-growpowerhub-com`/Growpowerhub, Rede1/CAD, setembro2026–dezembro2027, INATIVO/Não participa. Nenhuma campanha, gasto, rateio novo ou ativação web foi criada.
- Complemento aplicado: CAD `5.25113531901109983`,10linhas→1grupo. Fonte completa3079linhas→64grupos; CAD `26695.62944211482275458731`, USD `9115.547990376777624485`;63grupos anteriores preservados. Revisão855/audit2565, último dia completo29/09, zero blockers, replay `already_applied`.
-400testes sem skips, ensaio real sem escrita, backup/restore, release guard com catálogo prévio, API16competências e desktop/mobile passaram. Fonte de evidência: `reports/finance-growpowerhub-1554828914424156170.md`.

## Growpowerhub US — decisão1557017566923325465

- Rodolfo confirmou permanentemente Growpowerhub / `Us-shein-en` (chave técnica `us-shein-en`) na mensagem1557017566923325465, thread1545426987756298340.
- `pl_digital-trust_growpowerhub_us` → `growpowerhub.com` / US / `us-shein-en`. Reutilizar automaticamente em novos relatórios; essa combinação US deixa de ser pendência. Outros países ainda sem regra permanecem fail-closed.
- A nova regra US complementa a decisão1554828914424156170; não reclassifica o placement `_de` / `de-cc-de` nem o histórico alemão. Preservar gestor, sufixos de operação, moeda, rede e participação no rateio já existentes; não autoriza ativação de campanhas ou do rateio.
- Estado de publicação e conclusão da parcela05/10: checkpoint `ZEUS-FINANCE-GROWPOWERHUB-US-1557017566923325465`; evidências em `apps/finance-system/private/growpowerhub-us-1557017566923325465/`.

## Seis sites SHEIN US — decisão1557024816031342732

Regra permanente de Rodolfo, mensagem1557024816031342732 na thread1545426987756298340:

- `us-shein-en`: **yolo** (Yolokfx / `yolokfx.com`), `vizioid.com`, `escalatepower.com`, `growpowerhub.com`.
- `us-shein-es`: `mavroa.com`, `boostingecon.com` (identificador financeiro existente `boostingecon`; preservar esse ID, sem duplicar cadastro).

Essa lista confirma as classificações já existentes de Yolokfx, Vizioid, Mavroa e Growpowerhub US. Supersede somente a vertical US anterior `us-cc-en` de Escalatepower (1549411618570633227) e Boostingecon (1548317688051277918), que passam respectivamente a `us-shein-en` e `us-shein-es`. Mantém todas as decisões de gestor, fallback/operação, moeda, rede, status e rateio. Não altera a regra histórica Growpowerhub DE, não reescreve competências fechadas e não reclassifica automaticamente relatórios de dias anteriores.

No lote corrente05/10, a regra corrige apenas os dois metadados US de Escalatepower e preserva os valores, IDs e atribuição da fonte. Boostingecon não consta nesse lote. Publicação/readback e fechamento são controlados pelo checkpoint `ZEUS-FINANCE-GROWPOWERHUB-US-1557017566923325465`, com evidência em `apps/finance-system/private/shein-sites-1557024816031342732/`.

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
13. Notificar a conclusão conjunta de gastos e receita, uma vez por data/fonte, somente após conferência dos dois fluxos (Rodolfo1553778586807304213, supersede sucesso silencioso1549047147465281658). Reexecuções sem novidade não repetem a mensagem; falha de entrega permanece pendente e não muda sucesso financeiro nem provoca nova importação. Quando houver classificação pendente, notificar esta thread uma vez em mensagem normal e compacta: numerar cada exceção, explicar em uma frase o que foi identificado e o que falta, e fazer uma pergunta compartilhada sobre o mapeamento e sua permanência. **Formato de transporte confirmado por Rodolfo1552296415269617685:** usar `content` com `embeds=[]`, sem cartão/bloco de código; separar parágrafos e substituir jargão de cutoff/readback por último dia completo/conferência. Conteúdo acima do limite é dividido sem truncar exceções, com nonce estável por parte e mention somente na primeira. Readback obrigatório verifica o texto exato e ausência de embeds. Esta regra supersede o transporte anterior em embed; não altera o REPORT-INFRA de #alerts-infra. Não repetir blocos `Fato/Diagnóstico/Lacuna/Recomendação/Pergunta` por item. Confirmar que o restante já foi aplicado. Bloqueio técnico persistente continua sendo reportado após investigação/retry. Zeus permanece responsável por aplicar somente a decisão autorizada e validar o complemento e o cutoff.
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
