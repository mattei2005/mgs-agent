# Sistema financeiro MGS — direcionamento de produto

**Vínculos/gestores confirmados1547052028663169105:** fonte canônica `docs/finance-account-ownership.md`. Nove contas ajustadas em setembro: Vizioid ativo/MGS; Yolokfx com cinco operadores; Mattei1→GameZoneAd; Infinitynexx titular Joe e conta G001 Ícaro. Pendências anteriores dessas duas últimas contas explicitamente supersedidas. Readback de cadastro, gastos e interface concluído.

Status: aplicação própria autorizada; homologação de agosto publicada com login e PostgreSQL 18 após confirmação crítica 1545934831664242748. Equivalência funcional integral ainda NÃO concluída; a planilha permanece fonte oficial.
Dono: Rodolfo Mattei. Orquestração: Zeus.
Fonte: discord:1545426987756298340:1545889371478167682.

## Horário e avisos vigentes — supersessão2026-09-09

Rodolfo1547235522055770142 mudou a rotina para perto das09h Eastern e autorizou atualizar o Dash novamente. Agenda física09:03:25 America/New_York (`3 9 * * *` +25s), primeiro minuto operacional livre próximo de09:00, informado na conversa. **Substitui toda referência histórica a07:16+25s abaixo.** O aviso curto após cada execução, inclusive sucesso, foi autorizado por1547230494289174719 e substitui a política anterior de somente exceções. Fonte: `docs/finance-daily-spend-notifications.md`; contrato `data/finance-media-spend-contract.json`. Reconsulta do mês até ontem, dedupe, proteção de valores manuais e FX permanecem. A atualização manual09/09 passou com14sites ajustados e replay seco sem alterações; os valores Meta de ontem continuaram revisando após09h, portanto não são fechamento definitivo. Primeiro disparo natural no novo horário ainda futuro.

## Direção vigente — API primeiro e gastos no relatório do site (2026-09-08)

Rodolfo `1547012165150711858` corrigiu a função da tela Contas de Anúncio: somente cadastro/vínculo. `1547015219325444107` autorizou descobrir primeiro na API as contas com gasto, cadastrar automaticamente as novas no Dash e vinculá-las ao site existente correto quando inequívoco. Gastos são preenchidos por conta/data no **Relatório Diário do site**, nunca em um painel de gastos no cadastro. O destino dos avisos foi confirmado nesta thread por `1547016066645889074`: novos cadastros/vínculos e exceções acionáveis, com dedupe; sem inventário diário de contas sem gasto.

**Supersede expressamente** o comportamento da primeira versão1546991137171181578: universo limitado ao cadastro, proibição geral de autocadastro e Contas→Gastos importados. Permanecem idempotência, preservação de edições manuais/FX liquidado e demais competências, não ratear nem escolher bloco/site ambíguo, sem mutação de campanhas ou planilhas. Agenda07:16Eastern+25s permanece. Contas Google canceladas/encerradas são indisponíveis, não zero; falhas inesperadas continuam exceções.

**Validado em produção:** descoberta350;34Meta+2Google com gasto; seis contas Meta antes ausentes cadastradas/vinculadas e Gamingadx vinculado ao site;616registros conta/dia; repetição com zero alteração;15sites/30visões desktop/mobile no Relatório Diário; cadastro sem painel de gastos. Restam Mattei1 sem site inequívoco e Infinitynexx-MX-CC-ES-01 com bloco ambíguo. Há27Google canceladas/encerradas explicitamente indisponíveis. Avisos enviados e relidos. Primeiro disparo pelo relógio após o cutover ainda não ocorreu; execução manual integral foi validada.

**Continuidade do dia inteiro:** `docs/finance-decisions-2026-09-08.md` cobre as33mensagens de Rodolfo e indexa gestores/Ícaro, salários/saldos, contas reconciliadas, histórico de abas próprias, português, câmbio e gastos. Autoridades de persistência1547016192689049641 e1547016756709691412. Skill prioritária: `mgs-finance-dashboard/references/api-first-site-daily-spend.md`; contrato `data/finance-media-spend-contract.json`; evidência `apps/finance-system/private/spend-placement-1547012165150711858/`.

## Fonte do histórico e atualização manual — correção de 2026-09-08

Autoridade inicial: Rodolfo, mensagem1546975305216827412. **Supersessão pela mensagem1546991137171181578 e pela correção direta subsequente:** janeiro–julho devem mostrar os valores atuais das próprias abas mensais e seus blocos de sites; não o Caixa Sintético e não uma captura antiga mantida por decisão do agente. O refresh autorizado reimportou40abas mensais/gestores sem qualquer leitura de Caixa ou gravação na planilha. As versões antigas permanecem somente para auditoria; `master-history-source` aponta a versão ativa consultada pelo Dash. Total, Metade e Estimativa continuam medidas distintas. Nenhuma regra de agosto é aplicada retroativamente.

O botão Atualizar foi publicado com busca de câmbio sob demanda pelo worker existente, via Service Account canônica e com proteção de taxas fixadas. As sete competências históricas permanecem somente leitura. Fonte técnica e evidência: skill `mgs-finance-dashboard/references/manual-quotes-monthly-source.md`; `apps/finance-system/private/manual-quotes-1546975305216827412/`.

**Histórico da primeira integração1546991137171181578 — regras de cadastro/UI supersedidas acima por1547015219325444107:** Rodolfo autorizou preencher01–07/09/2026 no Dash e automatizar diariamente perto das7h. A importação está publicada: coleta oficial por conta/dia nas moedas e datas das contas, valida total diário contra o período e grava com chave única, sem duplicação. Agenda efetiva:07:16America/New_York+25s, mês corrente da data de ontem até ontem, com auditoria global de8dias. Preencher contas já cadastradas; contas acessíveis ausentes do cadastro são listadas/reportadas, nunca criadas automaticamente. Vínculo inexistente, mais de um campo elegível, moeda incompatível, edição manual divergente ou falha de API não podem provocar rateio inventado ou zeros falsos. O valor por conta fica visível em Contas→Gastos importados; somente vínculo inequívoco alimenta o resultado do site. Receita e fontes Sheets permanecem sem gravação. Contrato operacional: `data/finance-media-spend-contract.json`; referência: `mgs-finance-dashboard/references/daily-api-spend-and-history-refresh.md`. A rotina não faz importação automática de janeiro–julho nem altera campanhas.

## Decisão explícita e supersessão

Rodolfo esclareceu que o pedido de dashboard significa um sistema de operação financeira, não duas abas adicionais no Google Sheets. A interpretação anterior do agente, materializada em BASE_DASH e DASH EXECUTIVO, não atende ao produto solicitado e fica supersedida como objetivo de entrega. O histórico dessa construção e a auditoria permanecem preservados.

### Esclarecimento de escopo — Rodolfo, mensagem 1545891242615902340

Este esclarecimento supersede qualquer leitura restritiva dos exemplos da mensagem anterior: Rodolfo quer transformar tudo que está na planilha e a lógica de todas as fórmulas em um sistema. Adicionar/remover sites ou incluir países foram apenas exemplos de dificuldades, não uma lista delimitadora de funcionalidades nem uma prioridade de implementação aprovada.

Requisitos confirmados:
- Preservar integralmente a operação financeira representada na planilha: dados, entradas manuais, lógica de todas as fórmulas, regras, condições, exceções, dependências e resultados. A referência já identificada inclui CAIXA SINTETICO, toda a aba Agosto 2026 e as dependências e lógicas dos gestores; não reduzir isso aos totais do dashboard.
- Não limitar o produto a cadastros, gráficos ou aos exemplos citados. Qualquer exclusão, simplificação funcional ou entrega parcial deve ser explicitada e aprovada, nunca presumida.
- Converter a lógica financeira em funcionalidades e regras do sistema, sem exigir reproduzir o mesmo arranjo visual de linhas e colunas.
- Mapear cada função/regra existente para sua implementação e teste correspondente. A equivalência integral precisa ser demonstrada; uma amostra de KPIs iguais não comprova cobertura total.
- Tornar a operação mais fácil de manter sem exigir alterações manuais em várias fórmulas. Os exemplos de adicionar/remover site e incluir país permanecem casos de uso dentro desse escopo completo.

Na etapa de esclarecimento inicial não havia implementação. Esse estado histórico foi supersedido pela autorização 1545900695545192479 e pela homologação local documentada abaixo. Não houve autorização para apagar abas, modificar credenciais produtivas, conceder acessos ou abandonar a planilha.

## Desenho funcional recomendado por Zeus — proposta, não decisão aprovada

- Aplicação web com armazenamento estruturado; dashboard é uma das telas, não o produto inteiro.
- Cadastros de sites/domínios, países e vínculos site-país, parceiros, gestores e moedas. Um site pode ter vários países e segmentos sem duplicar suas receitas nos totais.
- Lançamentos/importações diários de receitas e gastos, despesas da empresa, funcionários e comissões, preservando origem, moeda, data e segmentação. Não presumir frequência ou integração de captura automática sem definir o fluxo.
- Motor central de regras por parceiro/site/período: conversão cambial, tráfego inválido, rev-share, impostos, despesas, comissões, lucro, projeções e definições distintas de ROI. Regras e exceções devem ser explícitas e versionadas; não transformar fórmulas erradas em regras do sistema.
- Resumo mensal equivalente a CAIXA SINTETICO, detalhamento equivalente a Agosto 2026 e visões por site, país, parceiro e gestor. Seleção do período sem duplicar uma estrutura de abas a cada mês.
- Novos vínculos site-país entram em consultas e totais dinâmicos, sem listas de coordenadas mantidas manualmente.
- Recomenda-se inativar cadastros usados em lançamentos, em vez de eliminar histórico. Mudanças de taxa/parceiro devem ter vigência para não alterar silenciosamente meses anteriores.
- Trilha de alterações, validações de vínculos obrigatórios, prevenção de reimportação duplicada, precisão monetária definida e testes automáticos. Não prometer ausência absoluta de erros.

## Base e gate de validação propostos

A auditoria de agosto é evidência de referência, não o sistema concluído:
`/root/mgs-agent/work/finance-final-reaudit-1545877165982355557/FINAL-SUMMARY.json`.

Antes da implementação, produzir mapa completo de campos/regras/telas cobrindo todos os blocos de agosto e Caixa, incluindo blocos inferiores, moedas, países, gastos, despesas, gestores, fechamentos e taxas provisórias/efetivas. O escopo confirmado não é apenas um painel com receita, gasto e lucro.

Recomendação de migração: importar uma captura auditada, congelar suas taxas para comparação, recalcular de forma independente e comparar resultados por dia/site/país/gestor/parceiro e total, com tratamento explícito de precisão/arredondamento. Testar cadastro de site, país adicional e inativação sem perder histórico nem omitir componentes. Operar em paralelo antes de propor qualquer mudança da fonte de verdade. Não interromper preenchimento das planilhas nem implantar sincronização bidirecional sem decisão específica.

## Escolha e autorização — 1545900695545192479

Rodolfo escolheu a primeira opção: aplicação web própria construída com apoio Hermes/Codex, banco relacional e motor financeiro determinístico. Autorizou construir a cobertura completa, importar Agosto 2026 e comparar com sua planilha. O gate exige paridade por componente e resultado, não somente um total coincidente. Não autoriza cobrança, alteração de credenciais, exclusões, publicação financeira sem proteção ou cutover da planilha.

A construção ocorre em `/root/mgs-agent/apps/finance-system/`; dados privados e banco ficam fora do Git. O ambiente inicial usa PostgreSQL embarcado (PGlite) local, sem instalação de serviço de sistema nem assinatura externa. A passagem para PostgreSQL de produção/hospedagem/login corporativo fica em gate separado. A fase de importação pode preservar fórmulas como especificação e grafo de migração, mas isso sozinho não conclui a conversão para regras de negócio sem coordenadas.

## Endereço escolhido — 1545920429879730237

Rodolfo definiu `dash.mgsdigitalcorp.com`, subdomínio de `mgsdigitalcorp.com`, como endereço do sistema financeiro na thread `1545426987756298340`. Esta decisão define o hostname; não significa que DNS, HTTPS, hospedagem ou autenticação já foram configurados. Preservar o domínio principal e demais serviços. Publicação financeira exige proteção de acesso e os gates aplicáveis; não expor a homologação local diretamente.

## Hospedagem escolhida — 1545922219161419777

Rodolfo escolheu `MatteiInc01` (RunCloud server `290075`, IP `162.55.28.178`) para `dash.mgsdigitalcorp.com`, na thread `1545426987756298340`.

Preflight somente leitura: API e SSH acessíveis; stack Nginx/MariaDB; Node global `v18.20.8`, Python `3.10.12`; aplicação exige Node >=22. Porta local 8765 livre; sem webapp com nome dash/mgs na listagem. Nginx canônico `/usr/local/sbin/nginx-rc -t` passou com aviso preexistente de ssl_stapling/certificado Wantabrand, fora do escopo. Não substituir Node global nem usar o MariaDB dos sites como banco financeiro.

Gate histórico supersedido: a confirmação crítica foi recebida na mensagem `1545928620462313645`. A configuração de hospedagem abaixo foi executada; continuam proibidos cobrança não aprovada, exclusões e troca da planilha.

## Hospedagem configurada — confirmação 1545928620462313645

- RunCloud `290075` / MatteiInc01: webapp custom `mgs-finance-dash` ID `3012868`, usuário exclusivo `mgsfinance` ID `2069220`. Credencial técnica no 1Password, item `MGS Finance Dash - MatteiInc01 - mgsfinance`.
- Hostname `dash.mgsdigitalcorp.com`: registro A `162.55.28.178`, proxied, TTL automático; certificado Let's Encrypt emitido e HTTPS validado. HTTP redireciona para HTTPS.
- Runtime privado `/home/mgsfinance/apps/finance-system`, Node isolado `v22.23.2`; Node global `v18.20.8` preservado. Serviço `mgs-finance-dash` ativo/habilitado, com `PrivateNetwork=true` e banco PGlite de homologação. Não foi instalado PostgreSQL produtivo nem alterado MariaDB.
- Todos os requests públicos fora do desafio ACME ficam em HTTP 503, com aviso de preparação e sem dados financeiros. Não é um login implementado e não é acesso ao sistema final. Bloqueio adicional: outros usuários de sites não leem source.json nem alcançam o loopback do serviço. Proxy está preparado, mas não pode ser liberado antes de adaptar e validar autenticação/Host/Origin e o transporte privado.
- Validação: 15 testes Python, suíte Node com persistência/restore e PARITY_PASS no servidor; cinco caminhos sensíveis verificados com TLS em origem e via Cloudflare. 77 webapps existentes e hashes de configurações Nginx anteriores preservados. Backup protegido pré-Nginx e backup consistente da aplicação em `/home/zeus/mgs-finance-backups/1545928620462313645/`.
- Cloudflare manteve SSL Full herdado; não houve alteração global. Antes de liberar dados, exigir validação estrita da origem no escopo do hostname, autenticação e backup externo. O aviso preexistente ssl_stapling de Wantabrand permanece fora deste escopo.
- Supabase é opcional, não foi contratado. PostgreSQL não tem custo de licença; hospedagem própria consome recursos já pagos e exige manutenção/backups. PostgreSQL local separado é recomendação de Zeus, não autorização inferida das perguntas de Rodolfo para instalar banco produtivo.
- Runbook: `apps/finance-system/deploy/README.md`. Evidências privadas: `apps/finance-system/private/deployment-1545928620462313645/final-summary.json`.

## PostgreSQL e login — confirmação crítica 1545934831664242748

Rodolfo confirmou PostgreSQL 18 local separado, migração com paridade/restore, login administrador rodolfo, transporte privado e TLS estrito no hostname. Essa confirmação supersede os gates de banco/login e o estado de preparação das seções históricas acima, sem autorizar cobranças, exclusões, outros usuários ou substituição das planilhas.

Implementado e validado: PostgreSQL 18.6 em prefixo privado `/opt/mgs-postgresql18`, serviço `mgs-postgresql18`, banco `mgs_finance`, peer pelo socket Unix sem porta TCP; aplicação em `/home/mgsfinance/releases/pg-auth-1545934831664242748`, via socket permissionado, PrivateNetwork e login real. Nginx/Cloudflare exigem HTTPS, com SSL strict somente no hostname. Node/libpq globais, MariaDB e 77 webapps preservados. Não houve contratação Supabase.

Acesso https://dash.mgsdigitalcorp.com/login; usuário rodolfo, senha exclusivamente no 1Password, item `MGS Finance - rodolfo - dash.mgsdigitalcorp.com`. APIs financeiras exigem autenticação. Sessões seguras, CSRF, limitação de login, revogação e auditoria por identidade foram testados. MFA ainda não foi implementado; recomendação futura, não política aprovada inferida.

Migração de todas as seis tabelas legadas conferida por hashes/contagens; backup PostgreSQL restaurado e transações/privilégios testados em banco isolado. Segunda cópia do dump no host Zeus com hash idêntico. Baseline continua PARITY_PASS e R$ 90.840,88; nove telas passaram no navegador e no viewport móvel. Nenhuma edição na planilha. Runbook ativo: `apps/finance-system/deploy/PG-AUTH-RUNBOOK.md`; relatório `reports/finance-system-pg-auth-1545934831664242748.md`.

## Revisão de experiência — Rodolfo, mensagem 1546003791583903905

Fonte: discord:1545426987756298340:1546003791583903905. Requisitos declarados em conversa de revisão; não representam implementação ou aprovação visual final. Rodolfo ainda tem outros pontos a apresentar. Primeiro discutir a planilha principal; a parte operacional dos gestores fica para depois, sem exclusão do escopo integral.

Esta revisão supersede a apresentação atual como experiência desejada, não as evidências históricas de auditoria:
- Fluxo central: buscar o site como no Ctrl+F da planilha, ver suas colunas e analisar no mesmo contexto. Incluir também as linhas inferiores de gastos, não somente receitas/totais; reduzir fragmentação e excesso de menus.
- Despesas da empresa: referência declarada M99:Q145; colunas `Despesa Tipo - Valor $ - Valor R$ - Status`; adicionar despesa extra, editar atuais e deletar uma despesa. Pedido de funcionalidade não autoriza excluir registros existentes nesta conversa.
- Despesas Funcionarios: estrutura equivalente; colunas `Gestor - Valor $ - Valor R$ - Status`, com operações equivalentes de inclusão, edição e exclusão. Não antecipar a discussão das outras funções dos gestores.
- Remover da experiência cotidiana os controles de cenário (seletor de referência auditada, Criar cenário, Congelar cenário) e o painel Reconciliação da captura/PARITY_PASS mostrados nos screenshots. Isso não autoriza apagar a auditoria ou os controles internos de validação.
- Ordem histórica da mensagem 1546003791583903905, supersedida pela 1546030544213516358 abaixo: receita gross; rev share; receita; impostos; Despesas da empresa; Despesas da funcionarios; invalidos; gastos com media; liquido net. Duas colunas monetárias: `$` e `R$`. Não inferir nova fórmula ou deduções duplicadas apenas pela ordem visual.
- Incluir estimativa do mês; em mês encerrado, ela deve coincidir com o líquido realizado, sem projetar crescimento. Rodolfo chamou agosto de fechado e informou literalmente `$ 17.899.90 - R$ 90.840.38`. Preservar esses tokens como referência declarada, sem normalização silenciosa nem validação contábil implícita. O documento histórico registra baseline R$ 90.840,88: reconciliar a diferença na fonte antes de fixar valores. Distinguir encerramento do calendário de liquidação cambial; esta fala não comprova recebimento dos parceiros nem revoga automaticamente a regra de câmbio provisório.

Estado desta revisão: requisitos documentados; aplicação, banco e planilha não alterados por esta mensagem. Fechar o entendimento com os demais pontos de Rodolfo antes de redesenhar por inferência.

## Fluxo diário e correção de usabilidade — Rodolfo, mensagem 1546005208675516447

Fonte: discord:1545426987756298340:1546005208675516447. Complementa a revisão anterior e supersede a interpretação de despesas de funcionários como lista puramente manual.

- Rodolfo consulta o overall em CAIXA SINTETICO e pesquisa domínio na aba mensal. A aplicação deve preservar a facilidade desse percurso, sem navegação fragmentada numa longa barra lateral.
- Rotina declarada: recebe relatórios do Google Ad Manager por e-mail, trata os arquivos no ambiente descrito literalmente como `cloud` (ferramenta não identificada nesta fala) e preenche receitas por site, país e gestor. Coleta também gastos das contas no Facebook e no Google e preenche a planilha; os cálculos superiores atualizam os resultados.
- Um mesmo site pode ser operado por múltiplos gestores. A atribuição deve preservar data/site/país/gestor e vínculo das contas de anúncio, sem duplicação do consolidado nem perda da contribuição individual. Não inventar rateios ou atribuir todo o domínio a um único gestor.
- Responsividade, neste contexto, inclui fluidez de consulta e edição, visão legível dos sites e seus resultados e menos navegação; não reduzir a demanda a adaptação para celular ou troca de cores.
- A experiência precisa permitir alimentação/correção operacional de receitas e gastos, não apenas exibir a captura importada. Importadores de relatórios são parte da cobertura ainda aberta; nenhuma integração automática de Gmail, Facebook ou Google foi autorizada por esta descrição da rotina.
- Despesas da empresa e de funcionários devem ter área restrita a Rodolfo. Trata-se de requisito de produto: nenhuma permissão ou identidade é alterada nesta etapa de discussão; implementação seguirá os gates de autorização aplicáveis.
- O preenchimento da principal alimenta as planilhas dos gestores; elas calculam automaticamente os valores a pagar que retornam à composição de despesas. A experiência precisa preservar essa dependência, sem exigir redigitar remunerações ou tornar comissões calculadas em valores manuais silenciosamente.
- Rodolfo citou R$3.000, 7% e menos de R$100.000 líquido como exemplos de uma regra de remuneração. A fala não especifica integralmente piso versus adicional, faixas, base líquida ou exceções. Ler as fórmulas efetivas e seus precedentes antes de implementar ou afirmar a regra; não generalizar para todos os gestores.
- O problema confirmado é operacional e visual, não só cosmético: a versão percebida como importação com menus não atende. Zeus deve traduzir a rotina em uma proposta concreta e compreensível, sem exigir que Rodolfo saiba especificar design ou engenharia.

Estado: esclarecimento documentado; sem modificação de aplicação, dados financeiros ou permissões. Prioridade de produto: acertar o fluxo principal e validar a proposta de experiência antes de expandir a apresentação atual. O escopo funcional integral continua preservado.

## Interface publicada — autorização 1546005809845243944

Rodolfo autorizou refazer a interface existente e esclareceu, durante a execução, a necessidade de área administrativa lateral para câmbio/despesas/funcionários, taxas automáticas até o pagamento, fixação da taxa efetiva e percentuais de inválidos provisórios até o demonstrativo. Esses requisitos foram implementados na revisão publicada, não apenas documentados.

Estado verificado: três destinos principais; busca por site e aliases de domínio comprovados; edição diária via entradas de origem; despesas com CRUD/status/exclusão reversível; remuneração calculada protegida; câmbio/inválidos administrativos. Seis telas passaram no navegador autenticado em 390/768/1440px, sem erros JS/overflow. Testes de escrita financeira ocorreram em bancos isolados; a captura original e as planilhas foram preservadas. A sincronização automática de cotações foi executada e o cron `685397627b29` está definido para 26,56 * * * *, com 25s de stagger (30 minutos, não a cadência inicial sugerida de 5). Valores fixados no pagamento são preservados.

Relatório/evidência canônicos desta revisão: `reports/finance-ui-redesign-1546005809845243944.md` e `apps/finance-system/private/ui-redesign-1546005809845243944/`. Skill: `mgs-finance-dashboard`, referência `ui-redesign-and-quote-lifecycle.md`.

Esta seção supersede o estado anterior de revisão somente documental. Não declara completa a migração nativa integral, não implementa importadores de reports nem altera usuários/permissões. A planilha continua oficial. Agosto exibe resultado integral e participação de 50% separados; a referência validada é US$ 17.899,90 / R$ 90.840,88 para a participação, sem forçar o valor divergente anteriormente digitado no chat.

## Ajustes publicados — Rodolfo 1546030544213516358

Fonte: discord:1545426987756298340:1546030544213516358. Esta revisão supersede a ordem histórica dos inválidos e a grade única que misturava países.

- Tela inicial: Inválidos imediatamente abaixo de Receita gross; mesma dedução e mesmos valores, sem dupla contagem.
- Movimento: ordenação alfabética padrão por família de domínio; domínio raiz antes dos seus subdomínios adjacentes. Ranking de destaque continua por receita.
- Apresentação de gestores: Não mapeado / NAO_MAPEADO, Geizian e G002 são exibidos como MGS, inclusive no filtro. Vínculos, IDs financeiros originais, fórmulas de comissão e permissões não foram modificados.
- Abertura do site: blocos verticais por país, preservando ordem da planilha e segmentos complementares/compartilhados. Exemplo validado: Eggbev US, BR e GB. Colunas da receita na moeda nativa, gross USD/BRL, inválidos, net, impostos, mídia, lucro e dois ROIs; dias editáveis e total de cada bloco.
- Ao final: consolidado por país e TOTAL DO SITE sem duplicação. Despesas do domínio e resultado atribuído aos gestores permanecem identificados separadamente; filtros não criam rateio de despesas.
- Corrigido o rótulo de moeda de entradas diretamente em GROSS_USD que herdavam CAD do nome do bloco. Correção visual pela coluna-fonte; nenhuma conversão ou valor financeiro foi alterado. Coluna CAD vazia na fonte permanece vazia.

Validação: 20 testes Python e 10 Node aprovados; navegador autenticado em 390/768/1440px, blocos, filtros, ordem, edição e ausência de overflow/erros JS; 2015 verificações CAD/GBP contra captura original sem divergências. Publicação somente de assets estáticos, com backup privado e hash remoto. Relatório: `reports/finance-ui-country-blocks-1546030544213516358.md`.

Esclarecimento ao Rodolfo durante a execução: lançamentos do Sheets NÃO sincronizam automaticamente com a dash e edições da dash NÃO escrevem no Sheets. A exceção é a leitura das duas cotações automáticas a cada 30 minutos, preservando taxas fixas. A planilha segue oficial; integração contínua e cutover não foram implementados nem autorizados por estes ajustes visuais.

## Consulta e conferência — Rodolfo 1546147880559968286

Fonte: discord:1545426987756298340:1546147880559968286. Revisão publicada e validada; supersede blocos de país sempre abertos e as opções Pendente/Pago/Agendado no formulário de despesa.

1. Blocos site/país, como Eggbev · US, expandem/recolhem pelo cabeçalho e entram fechados por padrão.
2. Aviso fixo “Alterações ficam na dash. A planilha não é modificada.” removido da interface. A separação entre planilha e dash permanece inalterada.
3. Movimento do mês permanece clicável dentro de um site: retorna ao portfólio, limpando seleção e filtros.
4. Resumo financeiro mostra cotações e percentuais de inválidos estimados/provisórios; parâmetros efetivamente confirmados mantêm o rótulo de confirmação. G1 é divisor, não cotação.
5. Despesas da empresa e dos funcionários aparecem juntas no resumo, em blocos completos somente para visualização; edição permanece no Administrativo. Valores USD/BRL, status e data são os mesmos dados da área de edição, sem nova cópia financeira.
6. Formulário de despesa possui apenas A conferir e Conferido. Conferido exige data da conferência explícita, validada e persistida (`checked_on`), exibida como DD/MM/AAAA. Voltar a A conferir limpa a data corrente e mantém a auditoria. Sem atribuir data de hoje ou transformar status históricos automaticamente. Arquivamento não equivale a conferência e preserva metadados anteriores.

Rotina declarada por Rodolfo: depois que as empresas pagam, confere todas as despesas, todos os gastos das contas de anúncio de todos os sites e todas as receitas. A semântica é conferência, não agendamento/pagamento. A implementação deste pedido adiciona status/data às despesas; não implica novos controles de conferência de receitas/mídia ou liquidação automática.

Validação: 20 testes Python e 14 Node, CRUD isolado e navegador público autenticado em 390/768/1440px sem erros JS; restauração de backup PG em banco isolado com data persistida e baseline protegido. Nenhum lançamento de teste financeiro em produção ou escrita no Google Sheets. Relatório: `reports/finance-ui-review-1546147880559968286.md`. Evidência privada: `apps/finance-system/private/ui-review-1546147880559968286/`.

## Atualização e hierarquia de consulta — Rodolfo 1546158286506561578

Fonte: discord:1545426987756298340:1546158286506561578. Ajustes publicados e validados; supersedem consolidado ao final da página, painel isolado Gastos e despesas do site, posição antiga de gestores e grandes cartões de cotações no resumo.

- Site: consolidado primeiro, despesas mensais em coluna própria e resultado após despesas; resultado atribuído aos gestores imediatamente abaixo. Depois vêm KPIs e blocos diários fechados. Painel separado de gastos/despesas retirado, sem remover a despesa do cálculo/exibição.
- Despesa do site não tem país atribuído na origem; aparece uma única vez no total, sem novo rateio. Filtros parciais não autorizam descontar todo o custo mensal de uma seleção. Nesse caso, resultado após despesas fica não aplicável e o total é identificado como seleção. Gestores continuam representando o mês/site inteiro.
- Resumo: barra compacta superior de cotações/inválidos, KPIs e bloco de resumo por país de todos os sites. Lucro por país é operacional, antes de despesas gerais/pessoal. As despesas da empresa/funcionários continuam readonly no resumo.
- Atualizar foi testado no endereço real: GET /api/workspace HTTP 200, sem buscar nova cotação Google. Servidor lê duas cotações a cada 30 minutos; tela busca os dados do servidor a cada 5 minutos. Outra tela acompanha pelo mesmo polling, não instantaneamente. Formulário aberto pausa o ciclo automático; aba suspensa pode atrasá-lo. Nenhum novo usuário/acesso foi criado.

### Lacuna funcional confirmada no rateio

A auditoria read-only confrontou a planilha atual e a captura da aplicação: 43 blocos, 30 ATIVO/13 INATIVO, B37=30, sem diferenças nas fórmulas/valores de rateio auditados. Troca de Eggbev para INATIVO apenas em memória reduziu denominador e zerou sua despesa. Isso comprova a execução da regra importada, não o fluxo nativo completo.

**Lacuna histórica, supersedida pela implementação 1546169687346249728 abaixo:** faltavam controle de ATIVO/INATIVO na UI e redistribuição de despesas nativas extras entre sites/atribuições importadas de gestores. Teste isolado: adicionar despesa TEST USD30 mudou despesas gerais em -30, mas o rateio dos segmentos permaneceu igual. Esta lacuna supersede qualquer interpretação de CRUD de despesas como cobertura integral do rateio. A fonte oficial e as fórmulas Google não foram alteradas; correção/migração funcional não foi disfarçada como ajuste visual.

Relatório: `reports/finance-ui-layout-1546158286506561578.md`; evidências `apps/finance-system/private/ui-layout-1546158286506561578/`. Validação: 20 Python/17 Node PASS, browser público 390/768/1440px, testes de refresh manual/automático e duas telas (escrita somente em banco de teste), hashes de dois assets e três serviços ativos. Nenhuma alteração de backend, banco financeiro, autenticação, cron ou restart nesta publicação.

## Sites, parâmetros mensais e navegação — Rodolfo 1546169687346249728

Fonte: discord:1545426987756298340:1546169687346249728. Cadastro/rateio e refinamentos publicados e validados. Esta seção supersede a ausência de cadastro de sites/status e o não rateio de despesas extras documentados na revisão anterior. A iniciativa integral permanece aberta; não houve redução de escopo nem declaração de equivalência completa.

1. **Período (limite histórico supersedido por 1546184035921829938 abaixo):** Administrativo explicita Agosto 2026. Configurações e cadastros desta versão pertencem ao workspace mensal de agosto. Setembro ainda não pode ser aberto; a abertura de novos períodos deve separar entradas e resultados, com política explícita de herança dos cadastros e despesas, sem copiar resultados de agosto. Pergunta sobre setembro não foi tratada como autorização para fabricar dados ou abrir o mês com regras presumidas.
2. **Imposto e revshare:** C1=5% e D1=10%, lidos na planilha canônica via SA, aparecem como parâmetros percentuais editáveis do mês no Administrativo. Exceção M2 EW82=5% preservada; câmbio/invalids permanecem separados. Fixação de taxas de pagamento continua protegida.
3. **Cadastro de sites:** área administrativa mostra 41 rótulos de site agrupando os 43 blocos da origem e suas cotas/status. Openzed e Infinitynexx mantêm duas cotas cada; novo site entra com uma cota, sem inventar nova divisão da base existente. Ativar/inativar recalcula despesas, atribuições de gestores, folha e caixa; inativação mantém receitas e gastos já registrados. Cadastro novo exige país(es), parceiro, moeda e gestor explícitos e permite entrada diária nativa. Despesas extras e alterações de despesas da empresa passam a integrar o total rateado. Sem ativos com despesa existente é rejeitado, em vez de dividir por zero. A ponte de compatibilidade derivada atua apenas na cópia de cálculo, preservando fonte e fórmulas Google.
4. **País clicável:** a sigla no consolidado abre o bloco diário correspondente, rola e posiciona o foco no cabeçalho; blocos continuam fechados inicialmente.
5. **Contas de anúncio (limite histórico supersedido por 1546184035921829938 abaixo):** auditado o limite daquela versão. O editor altera valores em entradas mapeadas; ainda não há cadastro nativo para criar/renomear contas. Posições “US” sem nome não comprovam identidade de conta e não podem ser agrupadas por esse rótulo. Lançamento extra registra valores, não cria identidade de conta. Cadastro, vínculos e histórico de contas continuam no escopo integral pendente.
6. **Cores:** lucro positivo verde, negativo vermelho e zero neutro. ROI abaixo de -15% vermelho; entre -15% e 0%, inclusivos, amarelo; acima de 0% verde. ROI ausente continua não aplicável. Testes cobrem as fronteiras.

Validação: 23 testes Python e 19 Node aprovados; CRUD de site/status/receita e rateio em banco isolado; sete telas públicas em 390/768/1440px, sem erros JS/overflow; cálculo canário no runtime real e persistência/readback em PostgreSQL restaurado com papel mgsfinance. Captura original e baseline preservados; zero lançamentos financeiros de teste em produção e zero escrita no Sheets. Backup de código/banco restaurado e guardas de hash aprovados. Nenhuma mudança de schema, credenciais, permissões, cron ou gateway. Relatório: `reports/finance-ui-catalog-1546169687346249728.md`; evidências: `apps/finance-system/private/ui-catalog-1546169687346249728/`.

## Períodos até 2027, grupos de sites e contas — 1546184035921829938

Autorização nova de Rodolfo, na thread 1545426987756298340: tornar operacional todo mês de setembro/2026 a dezembro/2027 e cadastrar previamente esses períodos; dividir Movimento do mês em dois blocos, Sites Ativos e Sites Inativos; conferir continuidade de todas as regras para retomar em outra thread. Steering do mesmo turno acrescenta Cadastro de contas de anúncio com nome, ID e seleção do site em lista; buscar as contas já importadas pelo nome da planilha na BM acessível e cadastrar na dash. A operação Meta é somente leitura, não criação/renomeação/permissão na BM. Ambiguidades de nome/ID/site são bloqueadas para conciliação, nunca resolvidas por adivinhação.

**Publicado e validado.** Estado inicial autorizado/em implementação fica supersedido por este readback:

- Cadastrados os 16 meses de setembro/2026 a dezembro/2027, totalizando 17 períodos com agosto preservado. Receitas, gastos, despesas manuais e conferências de agosto não são copiados. Cadastros, status e regras fiscais/remuneração formam a referência inicial; alterações passam a pertencer ao mês escolhido. Calendário real, inclusive fevereiro/2027 com 28 dias e rejeição de entradas em dias inexistentes.
- Movimento do mês separado em Sites Ativos e Sites Inativos, conforme status do catálogo mensal, sem usar receita como critério. Totais históricos de inativos continuam visíveis; cotas e regras de rateio anteriores preservadas.
- Steering adicional de Rodolfo: na área de câmbio/inválidos, juntar cotações, inválidos, imposto e revshare em uma tabela compacta, com seletor de mês. Implementado; os seletores da página e do cabeçalho são sincronizados. Editar setembro não muda agosto. C1/D1 e exceção M2 EW82 preservados. Despesas mensais não são multiplicadas na projeção; período futuro sem dias completos não recebe previsão fictícia.
- Cadastro de contas com nome, ID, moeda e sites escolhidos em lista; identidade do ID/moeda preservada, nome local editável, vínculos de sites por mês. Não renomeia nem cria contas/campanhas na Meta. IDs das contas importadas foram validados em inventário somente leitura: 279 contas visíveis na BM Digital Trust, 78 identidades conciliadas e cadastradas. Novas contas já podem receber gastos diários, com recálculo de resultado/gestores/folha/caixa. O cadastro local é independente de sincronização contínua da Meta.
- Steering adicional de Rodolfo autorizou retirar campos genéricos como US ou similares sem preenchimento. 229 grupos vazios foram retirados do editor; nenhum campo com movimento foi ocultado e a fonte/histórico não foi apagada.
- **Pendência real:** sete posições nomeadas não obtiveram correspondência inequívoca e ficaram sinalizadas no cadastro: WANTABRAND FINANCE; Yolokfx · US-SHEIN-EN-01; Vizioid · MX-CC-ES-01; Creditoparaveiculo · BR-CAR-BR-015-G001; FinanciamentoAutoAdx; AutoCreditAdx; CarCreditAd. Valores preservados, sem IDs ou correções de nome inventadas. Posições Google não foram tratadas como contas Meta.

Validação: 19 Node/26 Python; todos os 17 períodos com calendário e readback em banco isolado, cadastro/reabertura e isolamento de edições, navegador desktop/celular local e público, atualização manual e polling com formulário protegido. PostgreSQL real restaurado e execução sob role mgsfinance, sem mudar HBA/grants. Produção: 17 meses/78 contas conferidos, baseline preservado, três serviços ativos. Zero lançamentos de teste financeiro em produção; zero escrita no Sheets ou na Meta.

Fonte operacional da continuidade: skill mgs-finance-dashboard v0.1.20, `references/monthly-periods-and-ad-accounts.md`; este documento e checkpoint ZEUS-FINANCE-DASH-AUGUST-20260904. Evidência: `apps/finance-system/private/ui-periods-1546184035921829938/`. Relatório: `reports/finance-ui-periods-1546184035921829938.md`. Limites anteriores de meses e cadastro de contas ficam supersedidos no escopo entregue, não apagados. Permanecem pendentes a conciliação das sete identidades e a migração nativa integral, alimentação/importadores/ciclo da fonte e eventual cutover final. Backup recorrente/DR e conferência de receitas/mídia não foram declarados implementados.

## Remuneração e vigência confirmadas — 1546380179654451281

Fonte: Rodolfo, discord:1545426987756298340:1546380179654451281; complementa 1546212978121117706. Supersede a dúvida histórica de fronteira/vigência: **resultado líquido de R$ 100.000 ou mais aplica 10% sobre todo o resultado; as regras de remuneração e atividade valem de agosto/2026 em diante, inclusive agosto**. Abaixo de R$ 100.000 aplica 7%, respeitando piso mensal de R$ 3.000 para gestor ativo, sem somar o piso à comissão. Inativo tem remuneração zero; Rafael e Gustavo gestores inativos. Salários fixos mensais: Samuel R$ 2.000; Ially R$ 7.000; Jislaine R$ 1.500; Raquel R$ 3.500; Kelly criativos R$ 3.000, separado de Kelly gestora. A base é o resultado líquido atribuído aos sites de cada gestor no mês, não uma nova distribuição inferida.

Autorização executada e validada nos 17 workspaces operacionais de agosto/2026 a dezembro/2027. Atividade editável independente de conferência, inativos zero, salários fixos e comissão sobre resultado líquido mensal com piso/faixa inclusiva persistidos; 32 testes Python/19 Node, integração e navegador local/público, backup PG restaurado e readback produtivo aprovados. Captura/baseline imutáveis de auditoria e Google Sheets permanecem preservados. Conferência é independente de atividade; `ok` histórico não foi convertido em nova conferência datada. Evidência: `apps/finance-system/private/payroll-1546380179654451281/`; relatório `reports/finance-payroll-1546380179654451281.md`. Isto supersede o estado de implementação pendente deste requisito, não o escopo aberto dos demais ajustes.

Os demais requisitos de 1546212978121117706 permanecem no escopo da iniciativa: trial paralelo de setembro, rótulos de parâmetros, Rede2 independente, Origem só interna, timezone/checkbox de contas e conciliação das contas COM gasto em agosto (sem pendência fictícia por rótulo sem gasto). Referência operacional: skill mgs-finance-dashboard, trial-payroll-review.md.

## Pedido integral e redes por site — 1546579646227943506

Fonte: Rodolfo, discord:1545426987756298340:1546579646227943506. Autorização para concluir integralmente os requisitos 1546212978121117706; a confirmação de entendimento referia-se apenas à remuneração, não bloqueava os demais itens. Estado inicial desta revisão: em implementação, não confundir decisão com publicação. Preservar a folha já aplicada e conferências reais posteriores; não reinicializar meses.

- Campo de rede editável por site e mês com SB Rede1, SB Rede2, ActiveView, Ymonetize, M2; percentuais/inválidos vinculados à rede correta. A SB tem duas redes independentes.
- Vínculos explícitos: Wantabrand e subdomínios → M2; AmazingXJobs → Ymonetize; WavesBee e subdomínios → SB Rede1; GameZoneAd, CreditoParaVeiculo e CarCreditAd → SB Rede2. Isto supersede o vínculo histórico WavesBee/YMonetize e a ausência de separação das duas redes SB nesses três sites. Demais sites exigem evidência na planilha/cadastro; sinalizar qualquer ausente ou ambíguo, sem atribuir por aproximação.
- Rótulos exatos: Imposto; Revshare Geral; USD → BRL; GBP → USD · YMonetize; Preço por Artigo; Inválidos SB Rede1; novo Inválidos SB Rede2 inicialmente 0,4104%, independente.
- Trocar JBF por SB na experiência do sistema financeiro. Preservar identificadores históricos internos, evidência imutável e configurações WordPress/ads fora deste escopo.
- Remover Origem das telas parâmetros/contas sem apagar rastreabilidade; editor de conta com timezone e sites por checkbox; conciliar todas as contas COM gasto em agosto contra a planilha. Sem gasto não constitui pendência de identidade.
- Revalidar remuneração/atividade/fixos desde agosto e meses novos A conferir sem herdar datas/status. Trial paralelo setembro continua; não escrever na planilha nem declarar substituição da fonte.
- Complemento explícito 1546593628602900673: Cliquet, Contecta Geral, Ducapes, Eggbev, TopFeed, Lyzmo, Newsoun, Openzed, Portal Relevante, SPE, Zuout e Zytiva, incluindo todos os seus subdomínios, pertencem à SB Rede1. Supersede a atribuição ActiveView importada dessas famílias; aplicar os percentuais SB e recalcular gestores. As cinco opções de rede continuam disponíveis, mesmo que uma rede fique sem site no cadastro atual.
- Critério de encerramento desta revisão: cada requisito rastreado a teste/readback publicado, ou bloqueio exato reportado. Não fechar por ter concluído somente a folha.

## Publicação e correção das planilhas — 1546579646227943506 / 1546593628602900673 / 1546595495726547094

Supersede o estado inicial em implementação da revisão anterior. Revisão publicada e confirmada na dash: 17 meses, cadastro de 41 sites com rede mensal, percentuais vinculados, SB Rede2 independente, rótulos solicitados, Origem oculta, timezone e checkbox de sites por conta. Distribuição atual: 35 SB Rede1, 3 SB Rede2, 2 M2, 1 Ymonetize; nenhuma atribuição ActiveView restante, mas a opção continua disponível. Remuneração/fixos/atividade e conferências anteriores preservados.

Autorização adicional 1546595495726547094 supersede a preservação absoluta de Sheets somente no escopo dos inválidos de Agosto 2026 e Setembro 2026. Aplicadas 4.202 correções de referências de fórmula e dois novos parâmetros M1 (SB Rede2 0,4104%, independente de L1/SB Rede1), com notas e formato percentual. Cobertura integral das 41 identidades em cada aba, incluindo linhas auxiliares dos gestores; canário e 4.204 readbacks de célula aprovados, zero alterações fora da lista, zero erros de fórmula, zero escrita de receitas/gastos. A captura imutável de homologação da aplicação não foi alterada.

Validação: 36 testes Python, 23 Node; migração/idempotência/readback dos 17 meses no PostgreSQL restaurado e em produção; browser local/público 390/768/1440; 28.548 comparações de valores diários planilha × dash sem diferença acima de USD 0,000001. Isso não prova equivalência funcional completa nem paridade futura com entradas ainda inexistentes.

**Duas diferenças de configuração de setembro fora da autorização de inválidos, a confirmar antes de ampliar a edição:** WavesBee está em CAD na planilha (`GP2=GROSS_CAD_US`, `GQ5=IF(GP5="","",GP5/$H$1)`), enquanto a dash herdava GBP; remuneração de setembro na planilha ainda tem IMPORTRANGE com literal Agosto 2026, causando valores de agosto para Nicolas/Isliago em mês sem movimentos. Não corrigidas silenciosamente. A folha de setembro na dash está com piso/fixos corretos. Não declarar setembro integralmente conciliado; tratar estes pontos como follow-up distinto, não como falha dos inválidos já corrigidos.

Conciliação de gastos de agosto: 324 posições examinadas, 49 com gasto, 44 IDs cadastrados com gasto e zero diferenças de valores de origem. Duas posições com movimento preservado sem ID inequívoco no inventário disponível: Yolokfx · US-SHEIN-EN-01 (USD 496,72) e Creditoparaveiculo · BR-CAR-BR-015-G001 (USD 311,02). Não são gastos ausentes nem autorização para inventar IDs. Cinco rótulos sem gasto da lista histórica não são pendência financeira.

Relatório canônico: `reports/finance-networks-1546579646227943506.md`. Evidência: `apps/finance-system/private/networks-1546579646227943506/`. Código: `network-rules.json`, `networks.py/.mjs`, `network-migration.mjs`. Fonte do trial: Rodolfo confirma que criou Setembro, ainda sem preenchimento; quer conferir o produto e então alimentar primeiro a planilha e depois a dash com os mesmos dados, sem sincronização bidirecional ou cutover.

## WavesBee CAD e releitura de setembro — 1546607083468623912

Rodolfo autorizou WavesBee em **CAD na dash e na planilha, exclusivamente Agosto 2026 e Setembro 2026**. Essa decisão supersede o GBP herdado nesses dois meses; não autoriza mudança de outros sites/meses ou do baseline imutável. Folha de setembro e G29 foram solicitadas como releitura/investigação, sem autorização nova de edição.

Publicado e validado: moeda de entrada CAD e conversão CAD / USD-CAD para USD nos dois workspaces; metadado mensal explícito `currency_policy=wavesbee-cad-1546607083468623912`. Editor público mostra CAD em ambos os meses. Na planilha, agosto recebeu somente GP2, GP3 e GQ5:GQ35 (33 células); setembro já estava correto e foi preservado. Todos os demais valores, fórmulas, conferências e cenários preservados; 17 meses verificados, baseline intacto, zero erros. Backup/segunda cópia/hash, restore PostgreSQL, prova com receita não zero em isolamento, API/migração e navegador público aprovados. 38 testes Python e 25 Node.

**Supersessão do apontamento histórico de folha:** a nova leitura SA confirma que O148/O149/O151/O153/O154 de Setembro já usam `Setembro 2026`, não Agosto. Nicolas/Isliago estão em R$ 3.000. Zeus não editou essas referências neste turno. Isso encerra a antiga pendência de literal do mês, não homologa integralmente os workbooks dos gestores: ainda existem referências ao câmbio Caixa J2 e células de projeção E14/F14 nas fórmulas de comissão; essas diferenças ficam como diagnóstico separado, não foram corrigidas por inferência.

`Setembro 2026!G29` da planilha principal pertence a Contecta Geral / US em 25/09. D29 (receita CAD) está vazia; E29 converte D29, F29 calcula inválidos e G29 retorna vazio por `IF(AND(E29="",F29=""),"",...)`. Fórmula presente e sem erro; não há IMPORTRANGE em G29. Nada foi preenchido ou alterado nessa cadeia.

Fonte de evidência atual: `reports/finance-wavesbee-1546607083468623912.md` e `apps/finance-system/private/wavesbee-1546607083468623912/`. A seção de duas diferenças de setembro acima é histórica e fica supersedida somente nos pontos expressamente fechados aqui.

## Complemento em execução — nome Wantabrand

Rodolfo pediu em mensagem nova durante a execução: `Wantabrand US-CC-ES + Wantabrand BR-CAR-BR` → `Wantabrand`, em sites. Nome de exibição publicado no cadastro, editor e lista de seleção de sites nas contas; identidade interna, IDs, valores dos vínculos e histórico preservados. Wantabrand Finance não foi renomeado. Sem novas escritas em banco/Sheets ou restart. Backup do frontend e hash reverso conferidos; 17 testes de interface passaram, além das suítes acima; navegador público validou cadastro/editor nos 17 meses e o valor interno do checkbox original. Evidências `wantabrand-deploy.json`, `site-display-tests.log`, `public-browser.json`.

## Próxima etapa

O redesenho acima está publicado; eventuais ajustes de uso partem desta versão, não do layout antigo. Continuar migração nativa integral (cadastros, vigências, inativação, períodos e demais fluxos). Consolidar política de backup recorrente, retenção/criptografia e observabilidade com os gates correspondentes; a cópia de implantação e o restore validado não provam DR contínuo. Manter a planilha intacta e não confundir banco/login publicados com produto integral concluído.


## Cobrança original, cadastro por ID e marca — 1546618148571058266

Decisão ativa de Rodolfo; complemento crítico do serviço `1546619674320441415` e logo/favicon `1546624782785716305`. Implementação/readback: `reports/finance-origin-1546618148571058266.md`.

- `FinanceTopFeed` é exibido como **Topfeed Finance**, na família Topfeed; ID, domínio finance.topfeed.fun, vínculos e histórico não mudam. TopFeed Finanzas continua separado. Alias Wantabrand preservado.
- Em novos cadastros de contas de anúncio, preencher apenas ID numérico; nome, moeda e fuso são retornados pela BM, readonly. Seleção dos sites continua mensal. Não cadastrar manualmente metadados que a BM não retornou; não criar/alterar conta na Meta.
- Consulta via serviço auxiliar aprovado em Zeus, utilizando as rotas já existentes de 1Password/SSH e inventário financeiro da BM Digital Trust. A aplicação continua sem internet e sem token Meta. Identidade/campos vêm do readback real, não de um inventário estático opcional.
- Em Despesas da empresa e Funcionários, valor/moeda de edição representam a cobrança/salário original: override explícito amount/currency quando existir, senão input/mode da importação. Nunca abrir a conversão USD como se fosse a cobrança original BRL.
- Cobrança BRL continua BRL e USD é derivado; cobrança USD continua USD e BRL é derivado. Comissões permanecem automáticas. CAD e quantidade/divisor preservam suas regras específicas.
- O sistema importou inputs e regras; não congelou todas as conversões. Câmbio automático/provisório é atualizado pelo coletor a cada 30 minutos; a tela consulta a cada 5 minutos (pausa durante editor). Cotação fixada no mês não é sobrescrita. Inclusive mês passado ainda provisório pode ter conversões variáveis até fixação. Editar na dash não escreve no Sheets.
- Logo e favicon derivados da mesma imagem oficial enviada, preservando desenho, cores e proporção. Login e aplicação usam o logo.
- Supersessão do esclarecimento da célula: Rodolfo corrigiu **G29 → G129** e informou que G129 já mostra valor. Nenhuma escrita em planilha por esse relato; o diagnóstico histórico de G29 não é uma pendência ativa.

Aceitação desta release: 40 testes Python, 28 Node, restore PostgreSQL/API com consulta Meta real e navegador público (17 competências, 56 editores, desktop/móvel, assets por hash, zero erros JS). Publicação code-only preservou registros financeiros/conferências por readback; não houve teste financeiro em produção, escrita na Meta ou no Sheets. Iniciativa nativa/trial e demais pendências históricas continuam separadas deste pedido.


## Movimento, extratos, aprovações e piloto Nicolas — decisão ativa 2026-09-07

Autoridade: Rodolfo 1546642267291394199; limite individual 1546642892427366510; confirmação e Geizian sujeito à aprovação + atividade exclusiva 1546643762686730382; dados da própria dash 1546645188523331624; piloto somente Nicolas 1546645785729572895. Thread 1545426987756298340. Registro: FINANCE-PAYMENTS-APPROVALS-NICOLAS-20260907.

Esta decisão supersede a restrição histórica de leitura de Despesas apenas a Rodolfo, **somente no aplicativo financeiro**, pelo modelo abaixo. Não muda autorizações de agentes/Discord nem aposenta as planilhas. O login Rodolfo e sua credencial existente permanecem intactos. As afirmações anteriores de que a apresentação de gestores ficaria para depois são supersedidas apenas pelo piloto Nicolas.

- Despesas da empresa passa a **Despesas Gerais**; rótulo “Despesa da planilha” removido; nomes visuais SB LeadsOn Hub / SB Tech Bot / SB Wire Fee; linhas compactas. A ordem alfabética desta decisão foi **supersedida por Rodolfo1547240897752604704**: de agosto2026 a dezembro2027, usar a ordem visual da planilha/prints, mantendo os nomes atuais SB. Agosto mantém sua origem; setembro confere sua aba; outubro2026–dezembro2027 recebem a base original/moedas de setembro, sem copiar conversões ou cotações. Implementação e evidências: `docs/finance-company-expenses-order.md`. Identidades, status e registros de conferência preservados.
- **Movimento Financeiro**, **Domínios** e bloco **Total do Site** antes dos países. Consolidados diário/mensal apresentam origens CAD/USD, gross normalizado e deduções, líquido final e ROIs. Inválidos/revshare não são deduzidos novamente do net. ROI NET segue receita após rede / custos absolutos − 1, e o mensal usa somas, não média dos dias. Rateio mensal do site aparece no Total do Site; pessoal não é inventado por país/site.
- Rodolfo é administrador e aprovador. Geizian tem leitura financeira ampla e pode propor alterações de negócio/cadastros; nenhuma proposta altera o financeiro antes de Rodolfo aprovar. Aprovação e escrita de negócio são confirmadas na mesma transação, com proteção contra replay/revisão vencida. Senhas ficam em fluxo exclusivo de Rodolfo, fora de propostas/histórico/notificações.
- Histórico de login/alterações/propostas/decisões por identidade é exclusivo Rodolfo, com paginação e filtro. Menus escondidos não são barreira de segurança: permissões também são aplicadas na API.
- Gestores só recebem sua projeção individual, nunca o financeiro inteiro de um domínio compartilhado. **Piloto somente Nicolas**, somente leitura, a ser conferido/ajustado por Rodolfo antes de qualquer réplica. Prévia administrativa `/operations?view=manager`; o administrador permanece identificado como Rodolfo, sem impersonação. Dados atuais vêm do motor/DB da dash; o workbook é apenas referência de escopo/layout. Nenhuma consulta às Sheets alimenta a tela.
- Usuários são criados desativados; Rodolfo define/guarda a senha no 1Password e confirma ativação na UI. Nenhum usuário novo, senha ou convite foi criado nesta implantação. O único login real permanece Rodolfo.
- **Pagamentos e extratos em BRL**: devido do mês + saldo anterior + ajustes/reembolsos − pagamentos; Geizian recebe 50% do líquido após as deduções. Remunerações dos demais vêm do cálculo existente, sem virar inputs de comissão. Pagamentos têm descrição/valor/data e podem ser estornados com motivo, preservando histórico. Não há transferência bancária e nenhum movimento entra novamente como despesa geral.
- Saldo inicial de Geizian em agosto: **R$ 0,71**, confirmação 1546643762686730382, origem G129 raw 0.7133221368276281 preservada. Setembro não copia a referência legada a julho: carrega o saldo do extrato. Descrições H105:H110 sem valores não geram movimentos; quitações antigas sem data/valor de pagamento não são inventadas a partir do “ok”. Devido/saldo acompanham a base enquanto provisória; pagamentos registrados permanecem valores fixos em centavos.
- Notificações: aviso interno + Discord nesta thread, com link de revisão. Worker Zeus existente mantém credenciais fora da hospedagem; somente metadados da proposta saem do DB. Uma notificação por ciclo e timeouts limitados preservam a consulta BM; falha de Discord não derruba a consulta Meta. Nenhuma nova unidade, cron, porta ou credencial foi criada.

Publicação validada: 34 Node, 40 Python; restore PostgreSQL isolado com 10 negações de API para gestor, aprovação única/rejeição, remuneração própria, estorno/carry, origem cambial e baseline preservado. Navegador público: 17 competências, 44 despesas ordenadas com altura máxima 43px, 8 blocos Nicolas, desktop/celular, lookup BM preservado e zero erros JavaScript. Tabelas novas são aditivas e ficaram sem usuários/pagamentos reais. Canary Discord 1546666381532209203 teve readback real. Relatório: `reports/finance-payments-1546642267291394199.md`; evidências em `apps/finance-system/private/payments-1546642267291394199/`. A migração nativa integral/trial anterior permanece uma iniciativa separada; este pacote não declara o produto inteiro encerrado.

## Correção: prints de julho são referência, não regra financeira
Fonte: nova mensagem direta de Rodolfo nesta thread 1545426987756298340, após a resposta da release: “nao eh regra, eu faco isso so pra nao ter que mudar todos os dias na planilha de gastos ... soh te mandei os prints pra vc conferir o total ... de julho”.
**Supersessão explícita de FINANCE-AD-SPEND-MONTHLY-CLOSING-20260907:** Zeus promoveu indevidamente uma explicação operacional a regra ativa. O ajuste do último dia era um atalho manual para evitar retrabalho diário na planilha, não requisito para o sistema. As capturas de julho servem para comparar os totais e continuar o raciocínio da integração.
Não estão autorizados por essa explicação: critério geral de aceitação somente mensal, ajuste obrigatório do último dia ou trava de reimportação derivada desse atalho. A automação pela API continua sendo o objetivo; políticas específicas de ajuste/fechamento dependem de desenho confirmado, não dos prints. O total Topfeed 12319.31 é uma comparação observada, não uma regra de produto. Nenhum valor financeiro deve ser alterado por esta correção documental.
Histórico: a seção anterior atribuiu equivocadamente a Rodolfo um critério mensal exclusivo e preservação obrigatória do ajuste final. Esse entendimento fica retirado; histórico original permanece no registro supersedido e no audit/Git.

## Navegação e contatos — 1546682010066489394
Autoridade: Rodolfo 1546682010066489394, continuação 1546685677599465513 (capturas julho). Esta seção supersede somente a apresentação anterior Movimento Financeiro/Administrativo e a estrutura restrita do formulário de usuários; preserva regras financeiras, piloto exclusivo Nicolas e a migração integral em andamento.
- Ativo: Dashboard e Relatório Diário; Gestores expansível com Nicolas abrindo em nova aba ampliada. O restante da operação mantém o menu lateral, ocultável; grupo Administrativo retirado e seus destinos ordenados como Rodolfo pediu.
- Relatório: 31 dias+total no fluxo da página, sem scroll vertical interno. Desktop 1440px mostra todas as colunas; celular mantém rolagem lateral interna. Cores e números centralizados, origens CAD/USD separadas dos valores convertidos. Sites têm coluna GAM pela rede mensal; ativos sem limite de altura, inativos recolhidos. Resumo por país por último no Dashboard, despesas compactas.
- Usuários gerenciados: nome completo, e-mail, telefone e ID Discord editáveis com revisão e audit; senhas com confirmação própria, Rodolfo exclusivo e revogação de sessões. Bootstrap Rodolfo continua protegido. Não foram criados logins, trocadas senhas reais ou concedidos acessos.
- Solicitação de integração: gasto diário Meta/Google pela API, por volta de 7h do dia seguinte; conferência manual na semana de pagamento e tratamento de refunds. **Ainda não implantada/ativada**. Fuso de execução depende da resposta de Rodolfo. Gastos de mídia junto ao Relatório Diário, janela de reconsulta, snapshots e proteção dos conferidos são proposta de Zeus, não regra ativa.
- Preflight Meta: dois canários de julho bateram no total das capturas. Topfeed teve total Sheet/API igual, uma constatação de comparação de julho, sem aprovação de regra geral de fechamento. Observações de linhas Google ficam históricas, sem demanda de correção; total mensal Google ainda não validado pela API. API Google não testada por falta de developer token identificado; arquitetura proposta por SA corporativa, nunca retorno a OAuth pessoal Drive/Sheets.
- Validação desta release: 38 Node, 40 Python, PostgreSQL isolado e browser público 17 competências, zero JS, readback de valores financeiros preservados, backup duplo/restore. Relatório e pendências exatas: `reports/finance-navigation-1546682010066489394.md`.

## Google Ads MCC, Meu perfil e logo quadrado — 1546702931384991834
Autoridade: Rodolfo1546702931384991834; logo1546703031033405501; perfil/menu/acesso SA1546705557996699699; ativação API confirmada por Rodolfo e validada HTTP200. Fonte de execução: reports/finance-google-profile-square-1546702931384991834.md.
- Google Ads: item Google Ads API - MGS no1Password contém developer_token e login_customer_id. IDs de contas novas não precisam ser adicionados ao cofre. Cadastro da dash consulta a MCC813-701-6595 com SA corporativa e mostra contas disponíveis por nome/ID/moeda/fuso/status. Descobrir não significa cadastrar todas automaticamente nem criar contas no Google. Somente consultas de leitura na plataforma.
- Duas contas cadastradas e lidas de volta: Gamingadx-US-01 (278-030-0411, BRL, America/New_York) e Mattei 1 (517-249-8094, BRL, America/Sao_Paulo). Inicialmente sem vínculos de site/source_links para não presumir atribuições ou duplicar valores históricos. A importação diária de gastos continua separada e não ativa. Supersede a falta de developer token/acesso Google descrita no preflight anterior.
- Meu perfil no menu da conta permite editar nome completo, e-mail, telefone e ID Discord do próprio usuário, pela identidade da sessão. Usuários oferece Editar inclusive para Rodolfo; a proteção anterior de todos os dados do bootstrap fica supersedida apenas para contatos. Login, senha, role, enabled e permissões não mudam nessa edição. Alterações em terceiros por Geizian continuam propostas; edição dos próprios contatos é direta. Nicolas continua único piloto e nenhum novo usuário real foi criado.
- Usuários passa a ser o último item do menu. Logo passa a preservar integralmente a arte quadrada original1024x1024, sem recorte; supersede o crop anteriormente publicado. Renderização160x160 no login/112x112 lateral, proporcional. Favicon preservado.
- Publicado e validado: backups duplos/hash/restore isolado nas duas fases; perfis testados com os três papéis; Google/Meta via fila e API reais; duas contas salvas pela UI, readback e demais dados financeiros preservados. Browser desktop/mobile sem cortes nos estados validados e zero JS. Skill0.1.27. Nenhum gateway, schema/grant, credencial ou planilha alterado pelo Zeus.

## Texto do login — 1546717157868703805
Rodolfo aprovou o logo do login e pediu somente título **Fluxo de Caixa** centralizado, removendo o subtítulo “Acesso restrito · Homologação de agosto de 2026”. Publicado com readback/QA390 e1440px. Logo, campos/autenticação, aviso inferior e menu lateral preservados. A opinião sobre o logo lateral não autorizou alteração: reduzir/centralizar continua proposta de Zeus. Evidência: apps/finance-system/private/login-title-1546717157868703805/.

## Gestores: apresentação Nicolas e contraste dos totais — 1546719646919434370 /1546720000134483970
Publicado e conferido no navegador: resumo Nicolas com cartões e8domínios, valores pt-BR com2casas, datas completas31/30conforme competência, detalhe por total/país sem limite vertical, rolagem horizontal localizada. Totais existentes usam precisão interna antes de arredondar; valores/IDs/fontes/remuneração/permissões intactos. Colunas origem CAD e resultados USD identificadas separadamente; país não é moeda. Total mensal do ROI não é somado nem promediado. As duas referências7%/10% não são somadas. Piloto continua Nicolas somente.
Supersede a apresentação bruta de strings decimais e altura430px; não altera regra financeira. Contraste de subtotal corrigido também nos elementos internos para todas as telas que usam a classe. Somas do consolidado agosto/setembro auditadas independentemente por Decimal;−6.305,50 em setembro é compatível com rateio interno não arredondado, sem ajuste de último dia. Validação:48Node,42visões mês/bloco/país,390/1440px,0JSerrors, backupduplo/hash/restorePGisolado e fingerprints financeiros/API antes/depois idênticos. Fonte detalhada: reports/finance-manager-layout-1546719646919434370.md.

## Usabilidade, GBP automático, Nicolas e salário Jislaine —1546729477319696405
Fonte: Rodolfo nesta mensagem e continuações diretas no mesmo turno: criar usuário Nicolas; confirmação crítica “sim”; salário Jislaine3000em todosmeses. Esta seção supersede: sidebar somente proposta/branca, conta no topo, ROI mensal indisponível, inexistência de login Nicolas e GBP manual obrigatório **somente no mês agosto/2026 da dash**.
- Sidebar preta, texto branco, logo integral centralizado. Conta no rodapé esquerdo. Celular: botão fechar44px e fundo escurecido; navegação rola independentemente da conta.
- Nicolas: três cartões USD principal e R$ secundário, pelo câmbio/valores do próprio mês. ROI mensal bruto/líquido vem do total calculado no motor, não média diária. Sem gasto permanece indisponível. Identidades, fórmulas e moedas de origem preservadas.
- Histórico: datas PG serializadas corretamente e exibidas no fuso Nova York; atividades/antes/depois em linguagem humana; cartões no celular. Leitura exclusiva de Rodolfo mantida.
- Câmbio/Contas/Domínios com linhas compactas; funcionários com explicação clara das faixas de comissão e sem comentário final sobre planilha. Linguagem para leigos é preferência estável de Rodolfo.
- GBP→USD automático em agosto/2026, fonte corporativa isolada Google Finance: Sheet1Zk-b8OoaDHrvFtuerf5IuO2jx-phVWXMYi79yqVTZX4/A1, fórmulaGOOGLEFINANCE("GBPUSD"), configuração google-finance-quotes.json. Não alterou I1/planilha principal. Demais16competências preservam modo anterior; fixação manual ainda vence atualização automática. Coletor existente30min estendido para3cotações; sem mudança de cron/autenticação.
- Login real **nicolas**, role manager/manager_key nicolas, habilitado após confirmação adicional. Senha inicial no1Password em **MGS Finance - nicolas - dash.mgsdigitalcorp.com**; nunca exposta em Discord/logs. Logintestado em390/1440, somente visão/pagamentos/perfil próprios,10APIs globais negadas. Não concede autorização a bots/Discord, não libera outros gestores e não implementa expiração forçada da senha.
- Jislaine personnel|157 passou de R$1500paraR$3000 em **17competências: agosto2026–dezembro2027**, com revisão/atividade/ID/moeda preservados. Recalcula salário e resultado do mês; outros funcionários e pagamentos registrados preservados. Baseline, contas, perfil Rodolfo e dados fonte idênticos no readbackPGcontra backup. Não altera a planilha.
- Aceitação:52Node/43Python; regressão final10Node;52verificações(13seções×4larguras360/390/768/1440),28formulários;6visões do loginrealNicolas,0JSerrors. Backupduplo/hash/restores isolados; publicadose lidos de volta8arquivos do app, GBPauto e17salários. Lote atingiu420s após commits; retorno conferiu banco e retomou só readbackpendente/usuário, sem repetir salários.
Relatório: reports/finance-usability-1546729477319696405.md. Evidências: apps/finance-system/private/usability-1546729477319696405/. Não declara importação diária de mídia nem migração integral concluídas.

## Duas identidades de contas confirmadas —1546752274989191230
Rodolfo informou explicitamente os nomes/IDs abaixo; live Meta confirmou ambos na BM Digital Trust155263197283282:
- Origem `Creditoparaveiculo · BR-CAR-BR-015-G001` → `Creditoparaveiculo-BR-CAR-BR-15-G001`, ID `1063939172741186`, USD, America/Sao_Paulo.
- Origem `Yolokfx · US-SHEIN-EN-01` → `Yolokfx-US-SHEIN-EN-01-G002`, ID `7840111366055613`, USD, America/New_York.
Supersede a pendência de identificação apenas dessas duas posições. Cadastro80→82; dois vínculos de31dias,62chaves originais, sem novo gasto ou alteração de valores. Slots AJO46:76 e AGK46:76 mantêm nomes, sites e países da origem; nomes BR/G002 não reclassificam os países financeiros. Preservação comprovada de todos os cenários financeiros e valores anteriores; navegador390/1440 confirma as duas contas e ausência do aviso com valores pendentes em agosto. Não declara resolvidas posições históricas sem valores. Fonte operacional: master-ad-accounts, revisão4. Evidência: reports/finance-account-links-1546752274989191230.md.

## Histórico fechado janeiro–julho/2026 —1546757745078968381
Decisão nova de Rodolfo: trazer os meses fechados de janeiro a julho de2026 para visualização na dash, usando valores finais das abas da principal e dos gestores, sem reaplicar fórmulas/regras atuais. Agosto/2026 em diante continua no motor e políticas implementadas. Objetivo: dispensar a planilha para consulta, não mudar os fechamentos. O passo pedido agora é analisar todas as abas e informar viabilidade; nenhuma importação foi executada nesta etapa.
A regra de snapshot histórico supersede a obrigação de executar o grafo/fórmulas para esses sete meses apenas. Não implica usar prints, revalidar/reabrir fechamento, recalcular ROI/comissão/salários/câmbios ou propagar Jislaine3000retroativamente. Capturar valores numéricos e formatação/currency/date/origem; distinguir erros, zeros, vazios e indisponíveis. Preservar totais já existentes e granularidades principal/site/gestor sem somar representações duplicadas.
Leitura real:40abas mensais em6arquivos + CAIXA SINTETICO Jan–Jul,377907células mensais. Principal/Kelly/Isliago/Nicolas/Joe possuem7abas;George possui5(mar–jul), sem jan/fev. Calendário completo em todas40abas presentes. CaixaC:I contém sete colunas de dólarfechado e totais, sem erros.
Lacunas atuais: abril principalS19 contém texto waves no GROSSUSD do PortalRelevante, refletindo22erros em detalhamento/totais; Caixa do mês tem valores válidos independentes. Janeiro/fevereiro principal têm132/148divisões por zero emROI. Nicolasjan/fev contêmP1 eAF38 comREF; blocoAF38 referencia fontelegada1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso não acessível aoSA(Drive404). Não corrigir/adivinhar valores; sinalizar ausências e preservar a fonte.
Ícaro aparece em blocos da principal, mas não há planilha própria identificada nas fontes/Driveacessíveis. George é chave/documento separado, não alias confirmado. A associação de identidade precisa de Rodolfo.
Pedido de criarJoe/Isliago/Kelly/Ícaro é pendente, não permissão ativa. Runtime verificou apenasNicolas no cadastrofinance_users; rotas de criação e visão ainda bloqueiam gestores nãoNicolas. Expandir o piloto exige implementação/testes de isolamento por gestor e confirmação crítica de criação/ativação/credenciais; senhas no1Password. Não atribuir a visãoNicolas ou George aoÍcaro por conveniência.
Parecer: tecnicamenteviável como módulo histórico imutável e independente; fidelidade total de células hoje indisponíveis e identidadeÍcaro ainda precisam de definição. Relatório: reports/finance-history-feasibility-1546757745078968381.md. Nenhuma alteração Sheets/produçãofinanceira/usuários nesta análise.

## Gestores autorizados e resolução das ressalvas —1546858367635685396

Confirmação crítica de Rodolfo após a pergunta explícita de criação/ativação: Joe, Isliago, Kelly e Ícaro, cada um somente com seus próprios dados, senhas iniciais exclusivamente no1Password. Isto **supersede a restrição do piloto Nicolas** e a pendência de confirmação dos quatro acessos; mantém todas as proteções de proprietário, parceiros/aprovações, dados financeiros e bots/Discord. Não cria outro perfil de direção nem autoriza alterações por gestores.

Identidade canônica em `context/team.md`: George=Ícaro; manter nome Ícaro e login `icaro`, com adapter para book legado `george`, sem renomear grafo nem criar pessoa duplicada. Ícaro só começou a receber comissões em março2026; janeiro/fevereiro têm salário, não comissão, conforme explicação direta de Rodolfo no turno.

Entrega: quatro usuários ativos; cinco visões isoladas incluindo Nicolas já existente, respectivas remunerações/extratos/perfil; navegação de Rodolfo expõe prévia de cada gestor. Senhas geradas pelo1Password e itens lidos de volta. Testes52Node; restore PostgreSQL85visões(5gestores×17meses),396270valores e100negações; público5logins reais,10checks decompetência,10mobile/desktop e70negaçõesAPI,logout401/0JS. Dados financeiros preservados na publicação.

### Decisões diretas recebidas durante o turno
- Abril2026S19: Rodolfo apagou o texto incorreto; readback confirmou vazio e22erros anteriores resolvidos. Zeus não apagou essa célula.
- NicolasJan/Fev2026: ignorar as duas referências legadas de cada mês na fila de correções. Não as substituir por0, reconstruir números ou excluir os demais dados do Nicolas.
- ROIJan/Fev: Rodolfo autorizou corrigir a divisão porzero, sem mudar valores. Executado somente nos280ROIs antes comDIV0 (132Jan/148Fev), fórmula guarda denominadorzero e exibe vazio;canário+comparação integral confirmaram33165células numéricas e demais fórmulas/inputs intactos. Fonte não foi recalculada pelas regras atuais do sistema.
- HistóricoJan–Jul continua por valores fechados, sem importação executada neste turno.

### Saldo anterior: diagnóstico, não edição autorizada
Julho: valor emF129, nãoG129, é135.0062095139292 e já existia na captura anterior; vem deJunhoF132. AgostoG129 referenciaJulhoF132 e agora é **−749.2866778631869**, negativo, versus0.7133221368276281na captura anterior. Comparação com `private/navigation-1546682010066489394/july-sheet.json` identifica **JulhoO156/Jislaine−1500→−3000** como único input alterado emA99:O160;despesa adicional1500reduz metadeGeizian750. CadeiaO156→N156→N160→H136→I136→I137→F103→F132→AgostoG129. Pagamentos eJulhoF129preservados nessa comparação. Autoria da edição Sheets não identificada; o rollout anterior deJislaine na dash limitou-seAgosto2026–Dezembro2027 e não comprova autorização de retroatividade julho. Não restaurar/zerar saldo nem alterar folha de mês fechado sem decisão explícita. Abertura da dash de0.71permaneceu preservada; diferença para a planilha exige resolver o fechamento, não importação silenciosa.

Evidências e relatório: `reports/finance-manager-access-1546858367635685396.md`; `apps/finance-system/private/manager-access-1546858367635685396/`. A decisão sobre Jislaine/julho foi recebida depois e executada conforme a seção seguinte; esta descrição do diagnóstico não permanece como pendência ativa.

## Julho restaurado e requisito de saldo interno —1546866505663254599

Rodolfo confirmou: emjulho Jislaine1500; agosto3000. Executado exatamente `Julho 2026!O156=-1500`, backup/hash+readback, sem alterar pagamentos ou digitar saldos. `JulhoF132` e `AgostoG129` recalcularam de−749.2866778631869para0.7133221368276281. AgostoP157−3000preservado. Supersede o bloqueio de decisão do diagnóstico anterior.

Na dash, `personnel|157` deagosto jáestava3000 e permaneceu3000; extratoagosto saldoanterior71centavos; saldosposteriorescalculadosinternamente. Readback real: saldoagosto9152432centavos e saldoanteriorsetembro9152432centavos. Julho ainda NÃO está cadastrado/importado na dash; portanto não afirmar que uma folha dejulho na dash foi editada. Seus valores deorigemforamcorrigidos e devem compor a futura importação histórica.

Rodolfo confirmou a expectativa de que, após importarJan–Jul, o saldoanterior derive das contas da dash. **Critério obrigatório da futura importação:** incluir fechamentos, resultados prontos, ajustes, pagamentos e saldosanteriores, preservar os valores fechados/câmbios/regras históricas, e substituir o `opening=71` deagosto pelo vínculo ao fechamento dejulho dentro da dash. Não usarplanilhaemtemporealnemaplicarfolhaagostoaJulho. Importar somente blocosdesites/receitas/despesas não é suficiente para reconciliar o extrato. Até essa implementação, aberturaagosto continua exceção fixa importada; setembroem diante jácalcula carries internos. Não declarar o histórico importado ou a exceção removida antes do readback.

## Histórico fechado publicado e saldo interno —1546884731436671056

Rodolfo autorizou executar a importação Jan–Jul, fechamento/pagamentos/ajustes/saldos e ligação interna Julho→Agosto. **Esta seção supersede todas as pendências anteriores de importação histórica e abertura fixa de agosto.** Não altera a identidade/autorizações dos gestores, regras de agosto em diante, nem os valores fechados da origem.

Entrega verificada em `https://dash.mgsdigitalcorp.com/history`:40abas mensais de6fontes maisCaixaJan–Jul,377906células mensais/300089números idênticos e formatos/moedas preservados. PostgreSQLfinance_history guarda snapshot imutável por competência/livro; aplicação só tem SELECT. MenuHistórico fechado e seleçãoJan–Jul encaminham à visão histórica;17workspaces atuais permanecem no motor vigente. Gestores veem só os próprios dados/remuneração;Ícaro usa legadoGeorge,Jan/Fev mostram salário real sem inventar aba/comissão. NicolasP1/AF38Jan/Fev permanecem indisponíveis por decisão anterior.

Fechamentos, ajustes, pagamentos e datas disponíveis foram copiados, não inventados nem lançados novamente no ledgeratual. AberturaAgosto agora é calculada a partir do fechamentoJulhoF132 no banco interno:raw0.7133221368276281→71centavos, sem constante71/fallback nem consultaGoogle emruntime. Falta de fechamento bloqueia leitura em vez de forjar saldo. JulhoJislaine1500 e Agosto3000 preservados;Setembroanterior=saldoAgosto9152432centavos na conferência.

**Ressalva de origem preservada e visível:** nova capturaMarço fecha−67.10478401868022, masAbril abre0.7264772738271859. As fórmulas/inputsMarço não diferiram da captura de viabilidade; não há atribuição de autoria. Não se forçou igualdade nem se criou ajuste contábil. Cada mês usa seus valores fechados capturados, não regras atuais. Notas não financeiras com aparência de credencial ficaram protegidas fora da apresentação;nenhum númerofinanceiro omitido/alterado. Fórmulas e entradas originais não são expostas ao browser.

Validação:56testesNodePASS;restauraçãoPGcompleta,importação40payloads com readback exato,idempotência0duplicatas;stage217negações/85gestor-mesesatuais. Público6loginsreais,42gestor/proprietário-meses,84viewports,41negações,377906células idênticas e0errosJS. Serviçosfinanceirosativos;usuários/dadosatuais preservados. Nenhuma escritaSheets,credencial,transferência,configSO,gatewayrestart ou exclusão nesta tarefa.

Relatório `reports/finance-history-import-1546884731436671056.md`; evidências `apps/finance-system/private/history-import-1546884731436671056/`; skillfinanceira0.1.31 `closed-history-import-and-carry.md`. Backups duplos comhash/restore e stage retidos. Conclusão desta entrega não significa migração integral de todos os fluxos nem aposentadoria das planilhas.

## Mesmos menus para janeiro–julho — correção de Rodolfo1546896342805123125

**Supersede exclusivamente o desenho de menu Histórico fechado/redirecionamento acima.** A importação fechada, dados, isolamentos, remunerações e vínculo julho→agosto continuam válidos. Pedido inicial1546894693135028234 foi esclarecido por áudio1546896342805123125: importar todos os valores e apresentá-los na mesma estrutura de agosto, sem fórmulas atuais ou outro menu; saldo remanescente somente em Pagamentos.

Implementação publicada com os mesmos menus Dashboard, Relatório Diário, Domínios, Despesas Gerais/Funcionários, Câmbio/Inválidos, Pagamentos e Visão de gestor. Seletor permanece na tela; mês acompanha navegação. `/history` antigo encaminha ao menu nativo autorizado. Histórico permanece leitura-only. Tabelas diárias e totais são valores fechados; blocos inferiores e parâmetros originais incluídos. Pagamentos preservam cada ajuste/pagamento e saldo pronto; ausência de data/valor não comprova quitação. Não criar consolidados que faltam no layout antigo ou cadastro de contas inexistente na origem.

Fidelidade pré-publicação:64testesPASS;40documentos,504blocos,858headersGross sem omissão,194814valoresdiários conferidos;377906células completas preservadas. StagePG217negações/85mesesatuais. Cutover9arquivos confirmou valores históricos/dados financeiros/usuários intactos. Backup local+remoto e restore isolado verificados. Nenhuma escritaGoogle, credencial nova, transferência ou gatewayrestart.

Estado final de testes públicos e ressalvas em `reports/finance-native-history-1546896342805123125.md`; evidências `apps/finance-system/private/history-ui-1546894693135028234/`. Procedimento canônico skillfinanceira0.1.32, `references/native-closed-month-views.md`. Publicação não elimina a divergência março→abril nem converte as referências Nicolas indisponíveis em zero.

## SB Tech Bot em CAD desde julho/2026 — 1547697182948458611

Rodolfo confirmou a correção financeira: a despesa `company|142`, exibida como **SB Tech Bot**, mantém o valor original **629,28** e usa **dólar canadense (CAD)** desde julho/2026 e nos meses seguintes. Esta decisão supersede somente a origem `UNITS/divisor do mês` dessa despesa; não altera as outras despesas, moedas, cotações, conferências ou Google Sheets.

Julho/2026 fechado foi corrigido por supersessão versionada, preservando os seis documentos anteriores e as 40 linhas imutáveis de `finance_history`. O valor passou de USD -12,5856 para USD -448,01047977730474 pelo H1 do próprio mês; 4.086 células dependentes foram recalculadas nos documentos principal e dos cinco gestores, incluindo o fechamento interno F132 e o vínculo julho→agosto. Agosto–outubro/2026 já estavam em CAD. Novembro/2026–dezembro/2027 receberam 14 alterações; todos os 17 workspaces ativos agora retornam 629,28 CAD.

Backup duplo com SHA-256, restore PostgreSQL isolado, aplicação transacional, auditoria por ator/ação, segunda execução idempotente, readback 17/17 e navegador público 17/17 editores passaram. Zero escrita no Sheets, zero pagamento/transferência, zero credencial ou restart. Relatório: `reports/finance-sb-tech-cad-1547697182948458611.md`; evidências privadas: `apps/finance-system/private/sb-tech-cad-1547697182948458611/`.
