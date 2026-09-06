# Sistema financeiro MGS — direcionamento de produto

Status: aplicação própria autorizada; homologação de agosto publicada com login e PostgreSQL 18 após confirmação crítica 1545934831664242748. Equivalência funcional integral ainda NÃO concluída; a planilha permanece fonte oficial.
Dono: Rodolfo Mattei. Orquestração: Zeus.
Fonte: discord:1545426987756298340:1545889371478167682.

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

## Próxima etapa

O redesenho acima está publicado; eventuais ajustes de uso partem desta versão, não do layout antigo. Continuar migração nativa integral (cadastros, vigências, inativação, períodos e demais fluxos). Consolidar política de backup recorrente, retenção/criptografia e observabilidade com os gates correspondentes; a cópia de implantação e o restore validado não provam DR contínuo. Manter a planilha intacta e não confundir banco/login publicados com produto integral concluído.
