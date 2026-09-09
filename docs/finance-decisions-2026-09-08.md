# Financeiro MGS — decisões e continuidade de 2026-09-08

Dono: Rodolfo Mattei. Execução: Zeus. Thread: `1545426987756298340`.
Fonte primária da revisão: 33 mensagens de Rodolfo recuperadas diretamente do Discord, do início do dia Eastern até `1547016756709691412`. Evidência privada: `apps/finance-system/private/spend-placement-1547012165150711858/rodolfo-today.json`. As três mensagens sem texto são anexos/áudios; seu significado é recuperado das referências canônicas correspondentes, não inventado a partir de texto vazio. Captura não é uma nova autorização para repetir operações históricas.

Este documento indexa decisões; não duplica credenciais nem substitui banco/runtime. Para implementação, carregar a skill `mgs-finance-dashboard` e sua referência `api-first-site-daily-spend.md` primeiro.

## 1. Gestores e identidade
- Nicolas recebeu login de teste próprio, com acesso restrito à sua visão; senha provisória/custódia apenas no 1Password. Pedido `1546732650520125490`.
- Rodolfo autorizou os acessos de Joe, Isliago, Kelly e Ícaro no 1Password. George e Ícaro são a mesma pessoa; nome ativo Ícaro. Autoridade `1546757745078968381`, `1546858367635685396`.
- Nicolas em janeiro/fevereiro pode ser ignorado. Ícaro passou a receber comissões em março; antes, salário. `1546863148961767474`.
- Fonte de execução e validação: `mgs-finance-dashboard/references/manager-access-and-history-dispositions.md`; para Nicolas, `references/usability-google-finance-nicolas-jislaine.md`.

## 2. Jislaine e saldo anterior
- R$ 3.000 nos meses editáveis a partir de agosto; solicitação em massa `1546734939389694043` ; a confirmação curta `1546734960113877052` fica preservada no contexto do fluxo, sem servir como autorização isolada de novas mudanças. Implementação histórica cobriu as 17 competências editáveis, não uma alteração automática retroativa dos meses fechados importados depois.
- Exceção explícita posterior: julho mantém R$ 1.500; agosto mantém R$ 3.000. `1546866505663254599` prevalece sobre leitura genérica de 'todos os meses'. Janeiro–junho seguem as próprias abas fechadas importadas, sem aplicar regras de agosto retroativamente.
- Saldo anterior deve vir dos cálculos/valores internos do Dash, incluindo julho→agosto, não de um número manual congelado nem de nova consulta ao Caixa. A diferença transitória mencionada como 0,71 motivou essa exigência; não é um ajuste permanente para somar ou subtrair.
- Fontes: `references/usability-google-finance-nicolas-jislaine.md`, `references/closed-history-import-and-carry.md`. Questões/autorizações: `1546863148961767474`, `1546866505663254599`, `1546867429983133767`.

## 3. Contas reconciliadas por identificador
- Preservar as reconciliações de `Creditoparaveiculo-BR-CAR-BR-15-G001`, ID `1063939172741186`, e `Yolokfx-US-SHEIN-EN-01-G002`, ID `7840111366055613`. Não voltar a deixá-las pendentes por alias/importação de nome.
- Fonte: `references/explicit-account-source-reconciliation.md`; mensagens `1546749760726110260`, `1546752274989191230`.

## 4. Janeiro–julho fechado; agosto em diante calculado
- Importar janeiro–julho de 2026 para navegação e comparação, com os valores conferidos das próprias abas mensais da principal e dos gestores. Não reexecutar nesses meses as regras novas de agosto.
- Objetivo declarado: deixar de usar a planilha para visualizar esses meses; isso não autoriza apagar ou substituir as planilhas-fonte.
- Usar os menus existentes do sistema, não criar uma área de histórico separada. Valores fechados permanecem não editáveis pelo fluxo diário; versões antigas continuam auditáveis.
- Rodolfo corrigiu abril S19 por conta própria; isso não autoriza repetir a exclusão. ROI de janeiro/fevereiro pode ser corrigido somente sem alterar valores financeiros.
- A fonte histórica ativa é cada aba mensal e seus blocos de sites, **não CAIXA SINTETICO**. Essa correção substitui a antiga derivação pelo Caixa.
- A captura importada antiga não deve ficar como padrão quando divergir da aba atual autorizada: versões atuais foram reimportadas; anteriores somente para auditoria. Março: `G137` é total, não metade; o ponto conferido no Dashboard passou de US$ 49.687,43 a US$ 49.701,22. Maio tinha uma cotação volátil diferente entre capturas; não inventar valor nem rotular variação de cotação como fraude/erro contábil.
- Execução histórica: 40 combinações de abas mensais; fontes `references/closed-history-import-and-carry.md`, `references/native-closed-month-views.md`, `references/manual-quotes-monthly-source.md`, `references/daily-api-spend-and-history-refresh.md`.
- Autoridades e acompanhamentos: `1546757745078968381`, `1546863148961767474`, `1546875010143228035`, `1546881880299675719`, `1546884731436671056`, `1546894693135028234`, `1546896342805123125`, `1546975498872291440`, `1546981903955918848`, `1546991137171181578`, `1546991916539842580`, `1546992731446841484`.

## 5. Transcrição em português
- Rodolfo quer seus áudios transcritos em português, não traduzidos para inglês. Mensagem `1546894893916356779`.
- Preferência já faz parte da memória estável; procedimento/configuração fica em `hermes-agent-operations/references/portuguese-stt-language.md`. Esta revisão financeira não altera novamente config/gateway nem afirma um novo teste de áudio.

## 6. Botão Atualizar e câmbio
- O botão Atualizar deve solicitar a atualização das cotações e só depois recarregar os dados, preservando taxas fixadas/liquidadas e proteções contra edição/troca de período.
- Antes, apenas recarregava valores salvos. Não ressuscitar essa limitação como estado atual.
- Autoridades `1546974487419945082`, `1546975305216827412`; execução: `references/manual-quotes-monthly-source.md` e `manual-quotes.mjs`/worker/app.

## 7. Gastos de setembro e correção API primeiro
- O pedido Meta/Google de 1–7 de setembro é separado da importação histórica janeiro–julho. Primeiro houve consulta; depois Rodolfo autorizou preenchimento e rotina por volta das 7am Eastern.
- **Contas de Anúncio é cadastro/vínculo. Gastos ficam no Relatório Diário do site, por dia**, como o preenchimento das planilhas de cada site. O painel de gastos importados no cadastro foi rejeitado e não deve voltar.
- A API é o universo inicial. Descobrir contas com gasto, depois comparar com o cadastro; caso uma nova conta tenha gasto, cadastrar a identidade oficial, vincular ao site existente correto e preencher os dias.
- Auto-vínculo somente quando inequívoco por site/domínio/nome e país. Não criar site, escolher bloco ambíguo, ratear, mudar vínculo explícito ou transformar falha de consulta em zero.
- Rotina às 07:16 Eastern, com atraso de 25s, mês até ontem. Preservar idempotência por ID/data, moeda original, edições manuais, liquidações e demais competências/usuários/caixa.
- Notificar **nesta thread**, sobre novos cadastros/vínculos e exceções acionáveis. Não adicionar painel de notificação/gastos ao cadastro e não despejar inventário de contas sem gasto.
- Autoridades: `1546980491729571973`, `1546982020700315679`, `1546991137171181578`, `1547012165150711858`, **`1547015219325444107`**, destino confirmado **`1547016066645889074`**.
- Essas decisões substituem explicitamente 'somente contas cadastradas', 'não cadastrar automaticamente' e 'mostrar gastos importados em Contas' da primeira implementação.

## 8. Reconciliação da imagem do Facebook
- A imagem contém 34 linhas positivas, moeda USD, soma US$ 114.831,22; não mostra o período. A atribuição a setembro se apoia na conversa e na comparação com a API, não em uma data inexistente na imagem.
- A coleta anterior consultou 80 contas Meta cadastradas, mas somente 28 tinham gasto: US$ 111.206,16. O agente apresentou a cobertura parcial incorretamente.
- Seis contas fora do cadastro somavam US$ 3.623,67: Vizioid-US-SHEIN-EN-01-G002 e Yolokfx-US-SHEIN-EN-02-G006 /03-G005 /04-G004 /05-G001 /06-G003.
- Outros US$ 1,39 são diferenças entre os valores das contas nas duas capturas. Ponte exata: 111206.16 + 3623.67 + 1.39 = 114831.22. Não inventar que 80 contas tinham gasto nem que todas as 268 ausentes tinham gasto. A imagem diz USD; não converter para BRL porque a mensagem digitada usou R$.
- Fonte: `facebook-reference.csv` e referência API-first da skill. Mensagens `1547013148848955523`, `1547013269074612437`, `1547014179330719744`.
- Uma nova consulta pode produzir centavos diferentes; registrar momento/período/fonte e nunca ajustar um dia artificialmente para forçar igualdade com a imagem.

## 9. Continuidade solicitada
- Rodolfo exigiu salvar a skill e revisar **todas as decisões de hoje**, não só a última. `1547016192689049641`, `1547016756709691412`.
- Regra aprovada, implementação local, homologação, publicação e validação real são estados diferentes. Registro/checkpoint deve preservar essa separação.
- Recuperação: registro `data/knowledge-registry.json` → este documento/contrato `docs/finance-system-product-direction.md` → referência específica da skill → checkpoint `ZEUS-FINANCE-DASH-AUGUST-20260904` → evidência privada/runtime.

## Estado validado após o cutover
- Cadastro limpo publicado;15sites/30visões desktop/mobile conferidos após o preenchimento. Data diária usa o mês real.
- API-first exercitado em produção:350descobertas;34Meta+2Google com gasto;6novos cadastros Meta com site/país seguros e vínculo de Gamingadx;616registros conta/dia. Nova execução do mesmo snapshot alterou zero campos e preservou os demais estados.
-27Google com status oficial CANCELED/CLOSED são indisponíveis, não zero. CUSTOMER_NOT_ENABLED foi diagnosticado; não houve reativação, mudança de credencial ou repetição sem limite.
- Mattei1 continua sem site inequívoco; Infinitynexx-MX-CC-ES-01 continua com dois blocos elegíveis. Nenhum rateio/vínculo foi inventado.
- Avisos nesta thread entregues e relidos. Rotina permanece07:16Eastern+25s. Primeira execução pelo relógio após esta atualização ainda pendente; validação manual integral e replay realizados.
- Evidência de produção: `private/media-spend-runs/20260908T194649-0400/` e `20260908T195745-0400/`. Evidência de navegação/backup/85testes Node: `private/spend-placement-1547012165150711858/`.

## Transição anterior — histórico supersedido pelo estado validado acima
- UI de cadastro limpa publicada e validada em desktop/mobile; despesas existentes verificadas nos relatórios de 13 sites. Data diária corrigida para o mês real, sem `/08` fixo.
- Nova consulta API-first real: 350 contas descobertas, 34 Meta e 2 Google com gasto confirmado. Contas Google canceladas não aceitam a consulta; não são tratadas como gasto zero.
- Homologação isolada validou 6 novos cadastros, vínculo seguro de Gamingadx, 616 registros conta/dia, preservação do restante e repetição sem duplicação. Backend/rotina novos ainda requerem publicação e execução real completas nesta transição.
- Próximo passo Zeus: finalizar testes, publicar backend API-first, executar/validar produção e aviso; atualizar este estado, registry/checkpoint, inventário e REPORT-INFRA. Não pedir que Rodolfo repita o escopo nem tratar homologação como produção.
