# Atribuição de receita e sequência diária

## Autoridade e escopo

- Correção operacional: Rodolfo `1548113083774541935`, refinada por `1548133712795795506`, thread `1545426987756298340`.
- Dashboard/competências: `1548116691165384735`, `1548118576987242547` e `1548118811767607307`.
- Vale de setembro/2026 a dezembro/2027. Janeiro–agosto não recebem essa apresentação nem retropropagação.
- Fonte executável: `/root/mgs-agent/data/finance-gam-revenue-rules.json`; contrato: `/root/mgs-agent/data/finance-gam-revenue-contract.json`.

## Sequência diária obrigatória

1. O primeiro intake entre 08:00–08:30 que obtiver o par GAM completo valida todas as linhas e congela o plano.
2. Em seguida, o mesmo fluxo executa os gastos Meta/Google para a data exata do relatório.
3. Após state local e ledger PostgreSQL cobrirem essa data, importa a receita e avança o cutoff.
4. `09:03` para gastos e `09:22/09:31/09:41` para receita são somente fallbacks de recuperação.
5. Slots atuais do intake: `08:03`, `08:08`, `08:18`, `08:28` Eastern. `08:22` foi retirado após reconciliar o watchdog Hermes autorizado que passou a coincidir nesse minuto; auditoria de oito dias confirmou zero colisão operacional nos novos slots.

## Regra de gestor

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

## Dashboard e estado validado

- Contas de Anúncio mostra o quadro de atribuição de setembro/2026 a dezembro/2027; o mesmo documento global alimenta todas as 16 competências.
- Relatório Diário/Domínios deriva do Cadastro de Domínios. Readback de produção: 44 sites de catálogo e 44 sites de fatos, zero fato fora do cadastro, em cada uma das 16 competências.
- Receita de 10/09 finalizada sem mudar fontes/totais: 3.058 linhas → 58 grupos, CAD `28042.38632477471319015898`, USD `6303.6497353978632530296`, cutoff 10/09, revisão 138→139, audit financeiro 686, confirmação de regra 693, recovery `recovery-gam-reclassify-2026-09-10-0c26d8afe327`, replay no-op.
- GameZoneAd ficou integralmente em `g002-s`, USD `584.6281651473980147396`; os USD `140.302946934077980001` anteriormente atribuídos a `g001-s` voltaram para MGS conforme a correção.
- Browser owner: setembro e dezembro/2027, desktop/móvel, zero overflow e zero erro JavaScript. A auditoria posterior das abas de gestores passou 128 testes Node e 87 Python; detalhes em `current-manager-tabs-reconciliation.md`.
- **Sidebar, Rodolfo `1548141861066121257`:** remover o rótulo/link redundante `Financeiro` abaixo do logo. O logo permanece; `Dashboard` é o único item textual que abre a dashboard. Validar owner/partner, desktop/móvel e ausência de `.brand-section`.

## Geizian

A função `partner` está restrita aos menus pedidos: Dashboard, Relatório Diário, Gestores, Despesas Gerais, Despesas Funcionários, Câmbio e Inválidos, Pagamentos; Usuários, Aprovações, Histórico, Cadastro de Domínios e Contas de Anúncio ficam fora. O login `geizian` foi criado e ativado por confirmação crítica `1548133712795795506`, usando a senha já salva por Rodolfo no item 1Password `MGS Finance - Geizian - dash.mgsdigitalcorp.com`; a senha não foi exibida nem gravada em evidência. Readback: username `geizian`, e-mail `geizianpereira@gmail.com`, telefone `+55 87 9918-2658`, role `partner`, enabled=true, revision 1; login, sete menus, nove APIs permitidas, quatro negações, desktop/móvel e zero erro JavaScript passaram.
