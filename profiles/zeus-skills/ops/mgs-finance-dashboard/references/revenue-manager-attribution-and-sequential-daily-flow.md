# Atribuição de receita e sequência diária

## Ativação segura de novo mapeamento

Antes de tornar a regra consumível pelos crons, validar/criar o catálogo financeiro correspondente com backup e publicar a autorização do runner. Preparar o JSON, o código local consultado pelo preflight de hash e os testes em cópia isolada; ativar conjuntamente código local/remoto e regras canônicas somente quando catálogo e runner estiverem prontos, sob os locks canônicos. Não expor regra nova enquanto o site ainda está sendo cadastrado: um slot concorrente pode interpretar a lacuna transitória como falha real e emitir alerta. Depois, executar o complemento da mesma fonte, validar ausência de duplicação, cutoff e zeragem dos flags de falha.

Correção vigente Rodolfo1551947602562392085: `dicasfinancas` → `dicasfinancas.info` / BR / `br-cc-br`; sem medium canônico, fallback MGS/G002 com a regra de operação existente; gestores canônicos explícitos continuam prevalecendo. Nas linhas diárias parciais, exibir também o rateio diário de Despesas Gerais e Funcionários, incluído no resultado/ROI da linha, sem antecipar sua entrada no TOTAL REALIZADO. Evidência: `reports/finance-session-rateio-dicas-1551947602562392085.md`.


## Growpowerhub US — regra permanente adicionada

Rodolfo1557017566923325465 confirmou `growpowerhub.com|us` → `us-shein-en`; o placement `pl_digital-trust_growpowerhub_us` deve ser reutilizado automaticamente. Supersede somente o bloqueio anterior para US. A regra DE abaixo permanece para `_de`, assim como os fatos históricos; países ainda não confirmados continuam fail-closed. Preservar responsável MGS/G002, medium canônico, sufixos de operação, moeda, rede e rateio existentes. Estado de execução: checkpoint `ZEUS-FINANCE-GROWPOWERHUB-US-1557017566923325465`; decisão canônica: `docs/finance-gam-email-automation.md`.

Na complementação de um dia parcial, verificar os grupos reais antes de fixar a contagem: duas linhas do mesmo site/país podem gerar grupos separados `g002-d` e `g002-s`. Comparar dinheiro nativo, IDs, atribuição e metadados de fonte; o importador existente re-enriquece `quotes` com o câmbio provisório corrente ao completar a partição. Validar essa atualização contra a regra ativa em vez de exigir snapshots FX antigos, sem relaxar a preservação das demais chaves ou alterar a regra cambial.

## Growpowerhub DE — país/tag condiciona a reutilização

Rodolfo1554828914424156170: alias `growpowerhub` → `growpowerhub.com`; somente par `growpowerhub.com|de` → `de-cc-de`, responsável G002/MGS. Reutilizar automaticamente quando o placement continuar `pl_digital-trust_growpowerhub_de`; isolar outro sufixo e perguntar, sem herdar DE. O sufixo descreve as tags dessa operação, não prova geografia de visitante nem origem orgânica. Na fonte29/09,10linhas têm `mg01-d`; fallback existente preserva `-d` e produz `g002-d`. Medium canônico futuro mantém precedência. Site INATIVO/Não participa, Rede1/CAD. Decisão, catálogo e fechamento verificados em `docs/finance-gam-email-automation.md` e `reports/finance-growpowerhub-1554828914424156170.md`.

Ao ensaiar o complemento de um dia parcial, manter despesas mensais e unidades de rateio iguais; não exigir igualdade de `allocation.unallocated` depois de avançar o último dia completo. Validar que sua variação é exatamente mais uma parcela diária do mês, pois a conclusão do dia altera a alocação realizada sem mudar a regra. No cadastro vazio anterior ao complemento, a alocação inteira deve continuar idêntica.

Ao acrescentar uma autoridade GAM, conferir todas as expectativas de `mapping_authority_message_id`, inclusive testes históricos que consultam `load_rules()` global. O candidato pode usar regras locais em `build_plan` enquanto os testes carregam o JSON produtivo antigo por caminho absoluto: um gate pré-publicação verde não cobre essa segunda combinação. Exercitar a suite com as regras candidatas e novamente as regressões de mapeamento após o readback produtivo; corrigir expectativas de autoridade sem relaxar valores, países ou gestores. Mudança posterior somente nos testes deve ser publicada como lote separado, sem reiniciar aplicação nem reimportar receita.

## WavesBee US — principal e Finanzas

Rodolfo1553019425706217652 confirmou `wavesbeefinanzas` → `finanzas.wavesbee.com` / US / `us-cc-es`, distinto de `wavesbee.com` / US / `us-cc-en`; ambos Isliago/G003. Preserve a precedência dos media canônicos. O complemento24/09 foi CAD0.012742353809102358/g003-d, cadastro `site-wavesbee-finanzas`/WavesBee Finanzas, Rede1/CAD sem participação nova no rateio, setembro2026–dezembro2027.3000linhas→58grupos, audit2192, último dia completo24/09, replay idempotente. Fonte canônica: `docs/finance-gam-email-automation.md`; prova: `reports/finance-wavesbee-expenses-1553019425706217652.md`.

Ao preparar candidato isolado, incluir os helpers `deploy/` e todas as fixtures privadas efetivamente referenciadas pelos testes, além de source/domain/ui-model e manifest da fixture de fechamento. Rodar ambos os gates completos, nunca remover testes para contornar `ENOENT`/imports. Para runners financeiros de cron/recuperação, usar `/usr/bin/python3` explicitamente: o Python do Hermes pode ser uma venv sem openpyxl.

## Autoridade e escopo

- Correção operacional: Rodolfo `1548113083774541935`, refinada por `1548133712795795506`; Cliquet/PortalRelevante corrigidos por `1548716825418928213`, thread `1545426987756298340`.
- Dashboard/competências: `1548116691165384735`, `1548118576987242547` e `1548118811767607307`.
- Vale de setembro/2026 a dezembro/2027. Janeiro–agosto não recebem essa apresentação nem retropropagação.
- Fonte executável: `/root/mgs-agent/data/finance-gam-revenue-rules.json`; contrato: `/root/mgs-agent/data/finance-gam-revenue-contract.json`.

## Sequência diária obrigatória

1. O primeiro intake entre 08:00–08:30 que obtiver o par GAM completo valida todas as linhas, particiona `confirmadas` e `pendentes` e congela o plano.
2. Em seguida, o mesmo fluxo executa os gastos Meta/Google para a data exata do relatório.
3. Após state local e ledger PostgreSQL cobrirem essa data, importa imediatamente os fatos confirmados e os mostra no Relatório Diário como dia `parcial`. Se houver pendência, ela não vira zero e o cutoff/totais do Realizado permanecem no dia anterior; após a confirmação de Rodolfo, o mesmo import recebe somente o complemento e então avança o cutoff.
4. **Supersessão Rodolfo1553778586807304213:** enviar uma confirmação conjunta de gastos e receita após conferência, uma vez por data/fonte, nesta thread. Erro/parcial também recebe mensagem normal com causa, parcela já preenchida e decisão necessária. A etapa isolada de gastos não afirma completude da receita. Preservar retry seguro e dedupe; falha de entrega fica separada do sucesso financeiro, sem reimportar. **Formato confirmado por Rodolfo1552296415269617685:** enviar alertas GAM em mensagem normal (`content`), sem embed/cartão nem bloco de código, com parágrafos curtos e exceções numeradas. Explicar vertical e dia parcial sem jargão de cutoff/readback. Validar via GET o conteúdo exato e `embeds=[]`; documentação dizendo “mensagem normal” não prova que o transporte implementa isso. Se exceder o limite do Discord, dividir sem truncar exceções, com nonce determinístico por parte e mention apenas na primeira. Preservar deduplicação e política financeira; mudança de apresentação não autoriza classificar as pendências. REPORT-INFRA em #alerts-infra mantém seu embed canônico separado. Evidência: `reports/finance-gam-notice-1552296415269617685.md`.
5. `09:03` para gastos e `09:22/09:31/09:41` para receita são somente fallbacks de recuperação.
6. Slots atuais do intake: `08:03`, `08:08`, `08:18`, `08:28` Eastern. `08:22` foi retirado após reconciliar o watchdog Hermes autorizado que passou a coincidir nesse minuto; auditoria de oito dias confirmou zero colisão operacional nos novos slots.

### Identidade da caixa e recuperação

- Aceitar somente os endereços parseados exatos `admanager-noreply@google.com` (entrega direta diária) e `contato@marketingdigitalad.com` (encaminhamento manual de recuperação). O display name “Google Ad Manager” não substitui o endereço.
- `--manual-intake` recupera um falso negativo ou slot perdido executando a mesma cadeia intake → gastos → receita; ele não contorna classificação, backup, revision guard ou readback.
- `--dry-run` nunca altera o state operacional nem dispara notificação. Um resultado saudável de caixa limpa flags de falha técnica antigas; bloqueio de mapeamento não conta como falha técnica.
- Reutilizar mapeamentos já validados na mesma competência em vez de reabrir falsos bloqueios: Cliquet/GB → `gb-cc-en`/G002-d; Cephyric/FR → `fr-cc-fr`/G002-d; placement `topfeedfun` → `topfeed.fun`, TopFeed/US/`us-cc-en`/G004-d. Preservar o token original na linhagem.

## Regra de gestor

**TopFeed BR / FinanceAdx AR — Rodolfo1552302899483254856:** `finance.topfeed.fun|br` → `br-car-br`; `financeadx.com|ar` → `ar-cc-es`. Reuse existing FinanceTopFeed/FinanceAdx catalog IDs; do not conflate FinanceTopFeed with TopFeed principal or Finanzas. Retain currencies, networks and manager rules; the22/09 complements used CAD1.185705108781502/g004-d and CAD0.0011544944890569291/g006-d. Source3018rows→59groups, revision569/audit1983, cutoff22/09, zero blockers, idempotent replay. Source: `docs/finance-gam-email-automation.md`; evidence: `reports/finance-gam-layout-1552302899483254856.md`.

For preservation assertions, never index every mixed `additions` record solely by `id`: rate records can be keyed by `key` with no `id`, causing false collisions. Compare the unchanged partition structurally, or resolve each kind's canonical composite identity; retain strict source-entry validation for the import partition.

- `utm_medium` canônico `g001–g006` com `-d/-s` vence sempre, exceto em GameZoneAd. Isso permite que um gestor rode no site de outro sem alterar o responsável padrão do domínio.
- **Exceção GameZoneAd:** forçar qualquer medium histórico do domínio para `g002-s`. Rodolfo confirmou que nenhum gestor opera o site e que `g001-s` foi um erro de UTM na configuração inicial.
- Quando o medium está vazio, `-` ou não contém um gestor canônico, atribuir ao gestor responsável pelo site.
- O sufixo segue a operação da linha/domínio no relatório: ChatPion `-d`; tráfego direto `-s`. Sufixo explícito no medium sem gestor vence; senão usar a única operação canônica observada no domínio; sem evidência, usar a operação atual cadastrada. Operações conflitantes e sem identificação bloqueiam.
- Somente os compartilhados por todos — `fincgriffin.com`, `creditoparaveiculo.com`, `yolokfx.com` — retornam para MGS/G002 quando não há gestor.
- `openzed.com` aceita Ícaro em medium válido, mas ausência de gestor retorna para Isliago.
- Medium original permanece na linhagem para auditoria; nunca normalizar o valor-fonte silenciosamente.

## Códigos por operação

- Ícaro: `g001-d` / `g001-s`
- MGS: `g002-d` / `g002-s`
- Isliago: `g003-d` / `g003-s`
- Joe: `g004-d` / `g004-s`
- Kelly: `g005-d` / `g005-s`
- Nicolas: `g006-d` / `g006-s`

## Responsáveis por domínio

- Nicolas: `lyzmo.com`, `finanzas.lyzmo.com`, `eggbev.com`, `finanzas.eggbev.com`, `financeadx.com`, `seuprimeiroempregoam.com`, `empleo.seuprimeiroempregoam.com`.
- Ícaro: `ducapes.com`, `finance.ducapes.com`, `wantabrand.com`, `finance.wantabrand.com`, `marevelx.com`, `conectageral.com`, `finanzas.conectageral.com`, `portalrelevante.com`, `finanzas.portalrelevante.com`.
- Joe: `topfeed.fun`, `finance.topfeed.fun`, `finanzas.topfeed.fun`, `infinitynexx.com`.
- MGS: `zuout.com`, `finanzas.zuout.com`, `cliquet.com`, `finanzas.cliquet.com`, `vizioid.com`, `gamingadx.com`, `gamezonead.com`, `gamehubad.com`, `financiamentoautoadx.com`, `financiarveiculo.com`, `autocreditadx.com`, `carcreditad.com`, `autolendpro.com`, `dicasfinancas.info`.
- Isliago: `zytiva.com`, `finanzas.zytiva.com`, `openzed.com`, `finanzas.openzed.com`, `xyvlov.com`, `wavesbee.com`, `finanzas.wavesbee.com`.
- Kelly: preservar o cadastro já validado de `newsoun.com`, `finanzas.newsoun.com`, `de.newsoun.com` e `helixenit.net`; a nova mensagem não retirou esses vínculos.
- Compartilhados por todos: `fincgriffin.com`, `creditoparaveiculo.com`, `yolokfx.com`.

`autolendpro.com` foi confirmado por Rodolfo `1548133712795795506` como o domínio correto e pertence à MGS com operação atual direta `g002-s`. O literal anterior `autolendpro.comd` está superseded e não deve continuar ativo.

Sites informados como sem operação: Escalatepower, Growpowerhub, Mavroa, Boostingecon, Zyclor, Jobscana e Cephyric. Receita histórica ou tardia nunca é apagada por esse status.

**Mavroa US — Rodolfo `1549069898674606352`:** o placement permanente `pl_digital-trust_mavroa_us` pertence a `mavroa.com`, país US, vertical `us-shein-es`. Enquanto o medium não identificar gestor canônico, usar MGS/tráfego direto `g002-s`; um medium válido `g001–g006` continua vencendo na própria linha. Esta regra vale para relatórios futuros do placement US e supersede o antigo limite “somente nesta revisão” de Mavroa; país novo continua fail-closed.

**Boostingecon — Rodolfo `1548317688051277918`:** pode receber receita orgânica residual mesmo sem operação ativa. O placement literal `pl_digital-trust_boostingecon_us` mapeia para Boostingecon / US / `us-cc-en`, sempre `g002-d` e estratégia de bot. De setembro/2026 em diante, o site fica `Não participa` do rateio das Despesas Gerais; isso não remove receita nem gastos dos resultados.

**Cliquet e PortalRelevante — Rodolfo `1548716825418928213`:** `cliquet.com` principal em BR é permanentemente `br-car-br`; medium ausente usa o cadastro MGS/bot `g002-d`. O placement `portalrelevante` pertence ao domínio principal `portalrelevante.com`, país US, vertical `us-cc-en`, Ícaro/bot `g001-d`. O subdomínio `finanzas.portalrelevante.com` é distinto e usa `us-cc-es`, também `g001-d`; nunca transferir o espanhol do subdomínio para o principal. O alias executável esperado do subdomínio é `portalrelevantefinanzas`.

**Xyvlov, Zuout e Zyclor — Rodolfo `1550483550027911290`:** `xyvlov.com` US usa `us-cc-en`; o placement `pl_digital-trust_zuout_us` pertence ao domínio principal `zuout.com`, US / `us-cc-en`; `finanzas.zuout.com` permanece separado, US / `us-cc-es`. O literal `finanzas.zuou.com` não é domínio/alias cadastrado. **Supersessão por Rodolfo `1551316692565499956`:** setembro de Zuout principal e Finanzas fica como está na fonte: G006/Nicolas e G002/MGS, inclusive antes19/09. O corte19/09 proposto em `1551312942182441111` não deve ser aplicado retroativamente; não transferir os seis fatos G006 nem repetir a dúvida. Preservar dados/importador de setembro. Agosto continua com MGS e com os destinos AV já aprovados. Zyclor usa o identificador operacional `zyclor`, país DE, vertical `de-cc-de` e fallback MGS/ChatPion `g002-d`; no catálogo financeiro permanece inativo, sob MGS, rede SB Rede1. O fechamento de 17/09 foi completado em 2.951 linhas → 60 grupos, revisão 396, audit 1418, zero blockers, cutoff 17/09 e replay `already_applied`.

## Dashboard e estado validado

- Contas de Anúncio mostra o quadro de atribuição de setembro/2026 a dezembro/2027; o mesmo documento global alimenta todas as 16 competências.
- Relatório Diário/Domínios deriva do Cadastro de Domínios. Readback de produção: 44 sites de catálogo e 44 sites de fatos, zero fato fora do cadastro, em cada uma das 16 competências.
- Receita de 10/09 finalizada sem mudar fontes/totais: 3.058 linhas → 58 grupos, CAD `28042.38632477471319015898`, USD `6303.6497353978632530296`, cutoff 10/09, revisão 138→139, audit financeiro 686, confirmação de regra 693, recovery `recovery-gam-reclassify-2026-09-10-0c26d8afe327`, replay no-op.
- Receita de 11/09 finalizada após a decisão Boostingecon: 2.480 linhas → 60 grupos, CAD `20589.60661244756023753937`, USD `6524.6875898867087362474`, cutoff 11/09, audit 725, recovery `recovery-gam-email-2026-09-11-aa6f539734a2`, replay `already_applied=true`; gastos e states terminaram `ok` com zero falhas.
- GameZoneAd ficou integralmente em `g002-s`, USD `584.6281651473980147396`; os USD `140.302946934077980001` anteriormente atribuídos a `g001-s` voltaram para MGS conforme a correção.
- Browser owner: setembro e dezembro/2027, desktop/móvel, zero overflow e zero erro JavaScript. A auditoria posterior das abas de gestores passou 128 testes Node e 87 Python; detalhes em `current-manager-tabs-reconciliation.md`.
- **Sidebar, Rodolfo `1548141861066121257`:** remover o rótulo/link redundante `Financeiro` abaixo do logo. O logo permanece; `Dashboard` é o único item textual que abre a dashboard. Validar owner/partner, desktop/móvel e ausência de `.brand-section`.

## Geizian

A função `partner` está restrita aos menus pedidos: Dashboard, Relatório Diário, Gestores, Despesas Gerais, Despesas Funcionários, Câmbio e Inválidos, Pagamentos; Usuários, Aprovações, Histórico, Cadastro de Domínios e Contas de Anúncio ficam fora. O login `geizian` foi criado e ativado por confirmação crítica `1548133712795795506`, usando a senha já salva por Rodolfo no item 1Password `MGS Finance - Geizian - dash.mgsdigitalcorp.com`; a senha não foi exibida nem gravada em evidência. Readback: username `geizian`, e-mail `geizianpereira@gmail.com`, telefone `+55 87 9918-2658`, role `partner`, enabled=true, revision 1; login, sete menus, nove APIs permitidas, quatro negações, desktop/móvel e zero erro JavaScript passaram.
