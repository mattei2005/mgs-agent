---
name: chatpion-bot-campaign-operations
description: "Opera campanhas Meta BOT/Messenger por contrato."
version: 0.1.1
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [chatpion, bot, messenger, meta-ads, campaign-ops]
    related_skills: [meta-campaign-engine-v3, meta-ads-intraday-operations]
---

# ChatPion BOT Campaign Operations

Contrato operacional reutilizável para campanhas Meta com destino Messenger apoiadas por uma estrutura ChatPion/DigitalTrChat. A skill controla Campaign Ops, relatórios e guardrails; não configura usuários, flows, drip, broadcast ou infraestrutura do ChatPion/DigitalTrChat.

## When to Use

Use quando uma operação estiver vinculada à família `chatpion_bot_messenger` e o pedido tratar de:

- regras e readiness da operação;
- criação ou clonagem de campanhas Meta;
- Corte e ROAS;
- Diário e relatórios read-only;
- elegibilidade, restrições e limites de Page;
- alteração durável da estratégia ou de um parâmetro operacional;
- sincronização das projeções canônicas nas threads Discord.

Não use para tráfego direto, quiz/SMS ou configuração do ChatPion/DigitalTrChat.

## Fontes canônicas

- Família: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json`
- Escolha corporativa do app BOT e readiness de migração: `data/ares/meta-ads/policies/bot-meta-app-selection.json`; decisão de app não comprova cutover nem troca o modelo de token.
- Consumidores: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json`
- Operação: caminho `operation_contract` resolvido no registro de consumidores
- Conta: caminho declarado pelo contrato da operação
- Threads: registry e prompts declarados pelo consumidor
- Engine de criação/clone: `meta-campaign-engine-v3`
- Política global de limites internos: `data/ares/meta-ads/policies/global-budget-limit-policy.json`
- Estado real: APIs, runtime, state e audit da operação

Enquanto a política global estiver `INACTIVE_UNTIL_EXPLICIT_REACTIVATION`, nenhum cap, piso, envelope, pool ou teto interno pode bloquear ou reduzir um pedido autorizado de qualquer consumidor ChatPion. O budget exato continua obrigatório; autoridade, pre-read/readback, billing, `account_spend_limit`, credenciais e automatic scaling permanecem separados.

Nunca inferir identidade, conta, Page, UTM, budget, threshold, horários, autoridade, cron ou write-enabled a partir desta skill.

## Resolução obrigatória

1. Resolver a thread ou `operation_id` no registro de consumidores.
2. Confirmar que o consumidor está `active`; candidato de onboarding não é operação ativa.
3. Abrir o contrato da família e o contrato exato da operação. Antes de carregar qualquer token ou chamar o runtime, resolver no registro institucional e no checkpoint a seleção vigente de perfil anunciante e app, seguindo a fonte canônica apontada; comparar essa decisão com os bindings da conta e do Engine. Um binding ainda instalado pode estar supersedido e não comprova qual identidade deve ser usada.
4. Carregar somente a rota pedida: `rules`, `campaign_creation`, `campaign_cloning`, `roas_cycle`, `daily_reporting` ou `page_guardrails`.
5. Consultar conta, runner, state e audit declarados pela operação somente quando a rota exigir. Em JSONs grandes, projetar primeiro os campos da rota e a conta exata; para checkpoints/registry, filtrar cada registro por request, thread ou chave canônica antes de imprimir. Não selecionar um contêiner inteiro porque sua representação contém o termo buscado: isso despeja registros não relacionados e pode truncar justamente a evidência necessária.
6. Falhar fechado quando houver binding ausente, ambíguo ou divergente.

### Mesmo app, credenciais por estratégia

- Ao receber uma decisão de padronizar o app de tráfego direto e BOT, preservar a distinção entre app emissor e identidade/tipo do token. Compartilhar o App ID não autoriza reutilizar o System User corporativo em BOT nem substituir o User Access Token do perfil anunciante aprovado.
- Tratar tokens como vinculados ao app emissor: não converter uma credencial alterando somente `app_key`/App ID. Descobrir ou obter o User token do mesmo perfil emitido pelo novo app, validar identidade/issuer/scopes e ativos reais e só então conduzir cutover staged com cache próprio, inventário completo e testes.
- Registrar separadamente escolha de app aprovada, credencial alvo ainda não validada, bindings efetivamente instalados e campanha autorizada/em hold. Uma escolha de app não emite/revoga tokens, amplia permissões, libera outro perfil ou retoma campanha pausada. Solicitar somente o gate novo indispensável, sem pedir de novo a escolha de app.
- Informar que usar o mesmo app concentra a dependência de disponibilidade/restrição da API entre estratégias, mesmo mantendo tokens separados; não prometer proteção contra restrições ou interromper tráfego direto para testar a migração BOT.

### Correção do perfil anunciante

- Antes de pedir login, OAuth ou verificação humana após erro de autenticação, conferir se a consulta usou o perfil/app atualmente aprovados. Um erro do perfil aposentado não estabelece uma obrigação de recuperá-lo; reconciliar a decisão vigente, sem testar credenciais alternativas por conveniência.
- Quando o operador identificar um substituto, recuperar primeiro a autorização canônica já existente. Se a validação estiver autorizada, testar a identidade e o emissor da própria credencial, a conta exata e somente a Page escolhida no pedido. Não exigir acesso a todas as Pages históricas da conta como condição para adotar o perfil.
- Separar **acesso validado**, **integração do executor concluída**, **pedido preparado** e **campanha publicada**. Uma leitura bem-sucedida com o substituto não muda os bindings do runner nem libera write; preservar o mesmo request, parâmetros e OK comercial durante a integração isolada e manter o gate posterior do manifest.
- Na resposta, corrigir brevemente a orientação anterior, informar os acessos realmente comprovados e nomear a camada ainda pendente. Não repetir uma ação humana que a seleção correta tornou desnecessária nem chamar o teste de acesso de migração concluída.

Para o diagnóstico protegido, carregar na skill `paid-acquisition-operations` a referência **Meta Facebook Login for Business — seleção de token**, seção **Validar substituição de perfil antes do cutover**.

## Responsabilidade operacional e encaminhamentos

Ares é responsável por conduzir os pedidos de Campaign Ops nas próprias threads, incluindo reconciliação de conta, finalidade, contratos e instruções dentro da autoridade vigente. Não mencionar nem transferir rotineiramente a Zeus a gestão de campanhas ou ajustes operacionais que Ares pode resolver. Divergência entre registro antigo e decisão autorizada não cria, por si só, uma dependência de Zeus: reconciliar as fontes no escopo permitido, preservando histórico e os gates próprios de publicação e budget. Encaminhar somente quando houver bloqueio real fora da autoridade ou capacidade de Ares, ou pedido explícito do usuário; nunca tratar o encaminhamento como conclusão. Esta autonomia não amplia contas, permissões, orçamento, credenciais ou Critical Subset.

### Alternativas antes do suporte externo

1. Antes de transferir ao operador a abertura de um chamado, avaliar em read-only as rotas já autorizadas para os mesmos objetos e se há outra capability instalada que preserve Page, mídia, copy, estrutura, budget e intenção de início. Se a sessão correta do Ads Manager estiver acessível e sua inspeção estiver no escopo, consultar o detalhe do mesmo anúncio em vez de pedir ao gestor que repita essa leitura; carregar `adspower-segurador-token-collector` e sua referência **PC1 Remote AdsPower Operations**. Tratar essa inspeção como diagnóstico, nunca como reparo ou autorização para editar/publicar. Nicolas prefere suporte externo somente quando não houver alternativa segura; um erro do caminho atual não comprova que o suporte seja a única saída.
2. Partir dos objetos já confirmados e das capabilities instaladas: comparar os deltas restantes com os modos registrados, as regras de lineage e o readback exigido. Preferir preservar campanha, conjunto, reservas e objetos válidos; não reiniciar a duplicação inteira para investigar uma falha em uma camada filha.
3. Classificar a conclusão como **rota instalada e autorizada**, **candidato dependente de aprovação/implementação**, ou **bloqueio que exige esclarecimento do provedor**. Uma proposta plausível não é um workaround validado: não prometer execução nem registrar como procedimento confiável algo que ainda não passou por implementação, testes e evidência real. Uma mudança de arquitetura recebe somente o gate técnico aplicável; preservar o OK comercial já concedido quando o escopo comercial permanecer igual.
4. Não contornar incerteza de efeitos com outro nome, outro request, outra interface ou conversão de clone em criação do zero. Preservar as solicitações incertas e os bloqueios de replay; suporte pode continuar necessário para resolver os efeitos antigos mesmo se uma alternativa futura for tecnicamente viável. Não garantir que o chamado se tornou desnecessário enquanto isso não estiver demonstrado.
5. Quando suporte for realmente necessário, explicar o resultado ainda ausente, as alternativas avaliadas e a limitação exata comprovada. Distinguir **erro confirmado**, **dependência causal identificada** e **reparo validado**: uma mensagem genérica repetida pela API/UI ou thumbnails HTTP200 não identifica a imagem interna rejeitada, não prova exclusão/permissão ausente e não libera substituição especulativa. Preparar no audit a hierarquia exata, erro/MID, leituras de controle e o detalhe que falta; pedir somente esse resultado diagnóstico ou a referência do atendimento, não outra captura genérica de uma tela já consultada. Distinguir **pacote preparado** de **atendimento aberto** e preservar o pedido/OK/ASAP vigentes; não pedir novamente aprovação de budget/publicação já válida.

## Definição de conta e finalidade da thread

Quando o operador apenas definir a conta e a finalidade de uma conversa:

1. Separar nome operacional, ID literal e observações internas. Não promover texto entre parênteses a alias operacional sem confirmação explícita; uma nota de referência não determina conta, estratégia, naming ou roteamento.
2. Validar o ID no checker de escopo corporativo e registrar o binding específico da thread na fonte canônica. Não usar a conta histórica do canal pai como fallback quando a declaração atual aponta outra conta.
3. Registrar somente o escopo solicitado. Definir uma thread para criação, clone ou duplicação não solicita execução Meta, migração de rotinas, ativação, budget ou automação, nem comprova readiness do contrato.
4. Se o operador corrigir a classificação de uma observação, corrigir o binding canônico e superseder explicitamente a interpretação anterior. Preservar nome e ID operacionais; não ampliar a correção a outras contas ou threads por semelhança de rótulos.
5. Validar o registro e responder brevemente com a conta e a finalidade confirmadas. Manter observações internas fora da identificação operacional; deixar preflight live e contrato exato para o pedido de execução correspondente.

## Precedência

```text
pedido atual explícito e autorizado
→ override ativo do contrato da operação
→ mecanismo da família
→ runtime/API para estado vivo
→ histórico somente para auditoria
```

Um parâmetro específico nunca sobe automaticamente para a família. Uma regra familiar nunca copia state, IDs ou autorização entre consumidores.

## Classificação de mudanças

### Mudança de família

É mudança no mecanismo reutilizável: sequência de gates, semântica de uma rota, contrato de readback, recovery, estrutura de aprovação ou política de projeção.

- atualizar skill e contrato da família;
- validar todos os consumidores ativos;
- atualizar as rotas afetadas e a thread Regras de cada consumidor;
- não copiar valores, IDs, schedules ou autoridade entre operações.

### Mudança de operação

É mudança de valor ou exceção: threshold, horário, budget, Page, evento, layout, hold, cron, fonte, autoridade ou capability de uma operação.

- atualizar somente o contrato, runtime e prompts da operação afetada;
- atualizar a rota funcional afetada e a thread Regras desse consumidor;
- não alterar outros consumidores;
- registrar a versão anterior como superseded.

### Simplificação de confirmações solicitada pelo gestor

1. Separar a aprovação do pedido atual da proposta de mudar pedidos futuros e classificá-la pela ordem real da conversa. Antes do resumo selado, registrar aceite comercial; depois do resumo e de esclarecimentos que confirmem o mesmo payload/digest, registrar o OK final e avançar o mesmo request, sem outra confirmação redundante. Não rebaixar um OK final válido a mero aceite comercial porque a mesma mensagem também pede uma dispensa futura ainda não ratificada.
2. Priorizar a experiência desejada pelo operador: pedido completo, execução autorizada e resumo verificado do resultado, sem perguntas ou confirmações redundantes. Conferir primeiro a autoridade e o contrato vigente para determinar quais confirmações são realmente obrigatórias; entendimento do processo, acesso técnico e escolha de budget não equivalem a poder remover um gate definido por outra autoridade. Distinguir correção necessária já coberta pela autoridade vigente de mudança estrutural sujeita a gate próprio; ausência de um modo no runtime não cria, sozinha, uma nova aprovação comercial. Se faltar confirmação técnica, formular uma única pergunta com alteração, conta e exclusões exatas, registrar o que continua pendente e interpretar a resposta no contexto. Não repetir a mesma cobrança, a mesma rejeição do preparador ou um resumo integral sem mudança material; isso transforma uma dependência técnica em loop de confirmações. Não anunciar execução antes de comprovar a admissão da rota.
3. Se o contrato exigir aprovação posterior a um resumo selado ainda não apresentado, preservar essa ordem. Não transformar um aceite antecipado em aprovação de um manifest futuro ou de detalhes técnicos ainda não informados. Explicar a diferença uma única vez, sem repetir a cobrança enquanto a preparação não estiver pronta.
4. Quando a dispensa permanente exceder a delegação vigente, capturá-la como candidato não ativo e encaminhar somente a decisão à autoridade competente. Não bloquear preflight, reconciliação, mídia ou plan por essa ratificação quando essas etapas já estiverem autorizadas; a campanha continua com seu dono e seus parâmetros originais.
5. Após eventual ratificação, superseder a regra canônica, integrar e validar o executor e sincronizar as projeções afetadas antes de anunciar a dispensa como ativa. Não gravar na skill uma exceção de uma operação como autorização universal de publicação.

### Regra de extração

Quando uma mudança específica revelar um procedimento reutilizável, promover somente o procedimento para a família. O valor continua no contrato da operação.

## Alterações de nome e continuidade do pedido

- Em perguntas como “qual nome você colocaria?”, consultar o mapping exato da Page, os históricos permitidos e o ledger em modo read-only; responder primeiro com o nome literal proposto, sem devolver placeholders quando os dados forem recuperáveis. Informar sucintamente a origem da identidade e se a numeração ainda não foi reservada, pois uma prévia não equivale a um manifest aprovado.
- Tratar testes de entendimento e prévias como leitura: não reservar sequência ou assets, fazer upload ou publicar sem pedido real. Preservar uma aprovação posterior no mesmo request, sem fazê-la valer como confirmação de mudança estrutural ou como prova de readiness.
- Separar uma regra prospectiva de naming de um pedido explícito para renomear o objeto atual. Não renomear campanhas existentes apenas porque o padrão futuro mudou; quando o operador autorizar o rename atual, executar essa alteração delimitada sem cobrar novamente budget, mídia ou OK comercial já concedidos.
- Resolver o alvo pelo ID persistido do pedido e confirmar sua hierarquia por GET. Não escolher apenas pelo nome ou pelo status ACTIVE: a campanha-modelo e a cópia publicada podem ter nomes semelhantes e ambas estar ativas.
- Tratar rename como alteração de metadata, não como nova criação ou recuperação do Engine. Enviar somente o campo `name`, preservar IDs e comparar antes/depois budget, status, conjunto, anúncios e tracking. Não reeditar manifests aprovados para fazê-los parecer criados com o nome novo; guardar separadamente o nome original e o nome atual confirmado.
- Se o nome consumir uma sequência compartilhada, verificar colisões e reservar o número para o pedido real de rename antes do write; depois do GET, vinculá-lo à campanha existente no ledger. Um número aplicado por rename já está utilizado e deve avançar o próximo pedido, inclusive em outra conta do grupo.
- Concluir com o nome literal confirmado e uma frase sobre os campos preservados. Detalhes de coordenação, digests e arquivos ficam no audit; não transformar uma correção simples de nome em nova rodada de intake ou explicação técnica longa.

Receita de rename, sequência e projeções: `references/thread-projection-and-synchronization.md`.

## Resumos de preparação e entrega Messenger

1. Conferir o JSON de cada anúncio contra o arquivo e o nome de template exigidos pelo contrato antes de compor o resumo. Não inferir inclusão apenas pelo nome da operação, pela Page ou por um anúncio amostrado; para a receita de envelope e conteúdo, carregar na skill `meta-campaign-engine-v3` a referência **Duplicação com Page, mídia e copy substituídas**, seção **Validação e relato do JSON Messenger**.
2. Mencionar explicitamente o **JSON Messenger**, o **nome exato do template** e a cobertura conferida em todos os anúncios, junto de Page, orçamento, início, mídia/copy e estrutura. Não deixar o gestor deduzir que o JSON está incluído porque o destino é Messenger. Não despejar o JSON inteiro nem anexar arquivo sem pedido.
3. Distinguir no texto **incluído e conferido na preparação** de **aplicado e conferido na Meta**. Reservar “criada e pronta” para a publicação e o pós-processamento efetivamente verificados; um manifest selado não comprova instalação do JSON nem agendamento remoto. No relatório final, declarar o template aplicado somente após GET dos creatives reais.
4. Se o gestor perguntar pelo JSON omitido no resumo, verificar os payloads de todos os anúncios e esclarecer o estado sem recriar ou alterar o pedido. Preservar resumo/digest; uma confirmação posterior ao esclarecimento aprova o mesmo plano quando não houve delta material, observados os gates vigentes.
5. Priorizar o relatório da campanha efetivamente criada, conferida e pronta, conforme solicitado pelo gestor. Para cada notificação interna, comparar a fase de entrega, o bloqueio e a decisão humana com a última mensagem antes de responder; uma conclusão de manutenção que não mudou esses pontos fica no audit/checkpoint, não vira outra confirmação comercial. Comunicar parcial somente por mudança material de fase/bloqueio, decisão necessária ou divulgação obrigatória de persistência. Consolidar divulgações de skill/memória com subsistema, alvo, lição e readback na menor atualização útil permitida, sem confundi-las com progresso de publicação e sem repetir contagens de testes, parâmetros ou ausência de ação humana.

## Rotas funcionais

### Regras

Mantém identidade, autoridade, precedência, readiness e mapa das rotas. Não executa trabalho funcional de outra rota.

### Criar campanhas

Fluxo: preflight vivo → Page/UTM → criativos reconciliados → pre-stage → manifest → validate/plan → resumo final → OK do request → Engine v3 → GET/readback. Defaults e campos obrigatórios vêm do contrato da operação.

### Clonar campanhas

O contrato da operação declara os modos suportados. Fonte, colisão de naming, Page, mídia, copy, JSON, budget e start são lidos ao vivo. Separe a finalidade declarada de aquecimento da Page da escolha da campanha-modelo: uma campanha usada para aquecimento em outra conta não vira automaticamente fonte de duplicação nem dependência do pedido atual. Resolva origem e destino pelo pedido vigente. Reconcilie a hierarquia com paginação completa e conte conjuntos/anúncios e seus estados em código; um sufixo no nome da campanha não comprova quantidade nem autoriza reativar filhos pausados. Schema/plan não prova readiness live; recovery reutiliza request e IDs.

Antes de reservar mídia ou anunciar execução, decompor todos os deltas solicitados: estrutura, Page, mídia, copy, tracking, nome e início. Conferir se um único modo suportado pela conta representa a combinação completa e aceita o nome aprovado; troca de Page combinada com criativos/copy novos não deve ser reduzida automaticamente a um modo que só suporte um desses deltas. Quando a fonte vier de uma rota que preserva seeds técnicos pausados, usar o classificador do runner registrado e confrontar os GETs com checkpoint/IDs/lineage; contar anúncios finais separadamente dos objetos técnicos, preservando o snapshot integral. Conferir cardinalidade e ordem dos slots, sementes PAUSED e vínculo de cada final à sua semente; nomes ou status isolados não autorizam excluir objetos da seleção. Para a modalidade de substituição de Page, carregar na skill `meta-campaign-engine-v3` a referência **Duplicação com Page, mídia e copy substituídas**, seção de reconciliação; o procedimento técnico pertence ao executor, não deve ser duplicado nesta skill. Se o runtime ainda exigir igualdade entre todos os objetos da fonte e a mídia solicitada, registrar a incompatibilidade antes de reservar/pre-stagear e conduzir manutenção isolada e testada. Não ativar/apagar seeds, filtrar silenciosamente a fonte nem corrigir o executor dentro da transação; uma correção instalada deve ser verificada antes da retomada, não solicitada novamente como se continuasse ausente.

Confrontar contrato operacional, contrato v3 e `config.accounts[account_id]`, incluindo `supported_modes`, flags de write e a policy de naming do modo. Uma regra salva e projetada não atualiza, por si, o validador do executor. Se houver divergência, distinguir regra registrada de integração executável pendente e apresentar o impedimento antes de pedir OK de publicação. Não editar o motor dentro da transação nem converter clone em criação do zero para contornar um gate; preservar o OK comercial, o horário literal e o request ao solicitar somente a decisão estrutural realmente faltante.

Para localizar uma fonte informada por nome:

1. Validar escopo da conta e fazer GET de `act_<account_id>` com `name,currency,timezone_name,account_status` usando a identidade anunciante declarada no contrato; um alias humano não comprova a conta live.
2. Paginar `act_<account_id>/campaigns` e comparar o nome literal em código. Se não houver match, procurar variantes de caixa/espaços apenas como candidatos, sem substituir silenciosamente a fonte. Confirmar o resultado vazio com uma consulta independente ao mesmo edge, usando `filtering=[{"field":"name","operator":"CONTAIN","value":"<nome informado>"}]` e `fields=id,name,status,effective_status`.
3. Com uma única fonte comprovada, ler seus conjuntos/anúncios e resolver Page/denylist antes de reservar assets, fazer uploads ou materializar o manifest. Não usar uma campanha parecida ou uma Page histórica para preencher a lacuna.
4. Se as consultas bem-sucedidas continuarem vazias ou houver ambiguidade, preservar o mesmo request com os parâmetros literais, evidências de leitura e próximo passo; pedir somente o link ou ID da campanha. Informar “não localizada pela API nesta conta”, não “não existe”: rascunhos não publicados e limitações de visibilidade não foram descartados por esse resultado. Se o operador autorizar expressamente qualquer uma das fontes de mesmo nome, considerar a escolha resolvida: selecionar deterministicamente uma candidata dentro do recorte autorizado, persistir seu ID e a autoridade e validar essa hierarquia por GET. Não pedir o ID novamente, alegar equivalência técnica sem comparação ou auditar todas as alternativas apenas para reabrir a decisão já delegada; qualquer incompatibilidade restante pertence à fonte escolhida ou ao executor, não à ausência de escolha humana.
5. Distinguir evidência de inventário de validação remota: nomes encontrados no inventário não comprovam presença live na pasta, metadata, elegibilidade ou pre-stage. No retorno, comunicar apenas a etapa efetivamente verificada e se houve write. Ao retomar, preservar budget/copy/arquivos e consultar a intenção temporal mais recente do mesmo pedido. Perguntar somente o novo início se o horário venceu e não houver uma instrução vigente e autorizada de início imediato; uma ordem explícita de ativar o quanto antes já resolve essa escolha, sem autorizar deslocamento silencioso para outro dia.

#### Retomada após correção do operador

1. Quando o operador corrigir o nome ou mostrar uma captura, registrar a correção no mesmo request, usar a lista da conta já obtida apenas para localizar o candidato e confirmar seu ID/hierarquia por GET vivo. Não repetir a busca completa nem pedir o ID se o nome corrigido já resolver uma única fonte na conta autorizada.
2. Se a fonte estiver sem anúncios, confirmar o vazio também em `GET /<source_adset_id>/ads?fields=id,name,status,effective_status,creative{id}` antes de explicar a dependência de lineage do modo contratado. Distinguir limitação do executor instalado de capacidade geral do Ads Manager; não converter clone em criação direta por inferência.
3. Quando o operador informar que publicou/criou o anúncio, reler imediatamente esse mesmo edge e persistir o `source_ad_id` encontrado. Um anúncio retornado com `status=PAUSED` ou `effective_status=IN_PROCESS` já resolve a ausência do objeto-fonte; não exigir sua ativação nem alterar a original apenas para obter lineage. Os demais gates de readiness continuam independentes.
4. Atualizar separadamente os bloqueios resolvidos e os restantes, preservando a primeira evidência no histórico. Não repetir uma instrução já atendida nem interpretar “tente novamente” como OK final de publicação. No retorno, informar o avanço real, o impedimento ainda comprovado e se houve write.

#### Substituição explícita de um pedido anterior

1. Distinguir correção do mesmo pedido de cancelamento com substituição. Quando o operador mandar desconsiderar o anterior e fornecer um novo alvo, localizar o request antigo pelo checkpoint e conferir seus efeitos reais antes de encerrá-lo; cancelamento da intenção não prova ausência de objetos já criados.
2. Marcar o request anterior como cancelado/supersedido conforme a ordem real e impedir retomada automática, preservando histórico, snapshots e IDs. Se o operador exigir cancelamento e um pedido novo independente, usar estado de cancelamento terminal da intenção, não apenas uma recuperação suspensa. Eventual referência ao novo pedido pertence ao histórico do cancelado, nunca a uma dependência executável do novo intake. Não apagar, pausar ou desfazer objetos externos apenas para refletir o cancelamento: esses efeitos exigem escopo e readback próprios.
3. Persistir no novo pedido somente os parâmetros expressos ou inequivocamente mantidos pela nova instrução e as políticas atuais que o operador mandou preservar. Manter identidade própria, solicitante, origem/destino e aprovações próprias; não herdar campaign/adset/creative IDs, fluxo entre contas, aprovação de manifest, recovery ou chamado de suporte do cancelado. Se já existe um registro independente correto, corrigir sua classificação sem gerar outro request desnecessário. Revalidar Page, tracking, elegibilidade, origem e mídia; não reintroduzir perguntas ou instruções abandonadas. A necessidade de corrigir o executor atual é uma pendência técnica do pedido novo, não continuação causal ou operacional do anterior.
4. Reconciliar reservas, sequência e uploads existentes antes de reservar novamente. Reutilizar efeitos compatíveis somente pelo mecanismo idempotente registrado; não liberar globalmente assets, reaproveitar número comprometido ou repetir uploads por supor que cancelar o pedido removeu seus efeitos.
5. Preservar o horário literal e separar intenção comercial de aprovação final. Se o início vencer durante manutenção/preparação, perguntar somente o novo horário quando o próprio pedido novo não trouxer instrução temporal vigente e autorizada que já resolva a escolha. Não transportar uma autorização de início imediato do pedido cancelado por inferência. Depois de preparar o novo pedido, apresentar seu próprio resumo selado e exigir o OK posterior aplicável. Uma notificação tardia de manutenção nunca reabre o pedido cancelado.
6. Conferir a separação nos registros consumidos pelo runtime e nos checkpoints: cancelado sem próximo passo de execute/recovery, retomada antiga bloqueada, coordenação reconciliada, novo intake sem dependências antigas e somente contas-fonte/destino atuais. Responder primeiro com o cancelamento efetivo e o escopo novo, em poucas linhas; não repetir a narrativa anterior nem apresentar limpeza de registros como campanha criada ou reparo do executor.

#### Alteração após o resumo e confirmação curta

1. Decompor a resposta ao resumo em aprovação e deltas: horário, status, quantidade e eventual exclusão. Uma instrução condicionada à remoção de objetos não aprova silenciosamente um plano que os preserva.
2. Se o operador pedir remover anúncios técnicos que o modo contratado exige preservar, explicar uma vez a diferença entre os anúncios finais e os técnicos pausados e perguntar somente se aceita essa preservação. Não excluir objetos da fonte nem trocar a arquitetura para satisfazer a condição por inferência.
3. Vincular uma confirmação curta à pergunta imediatamente anterior. Se ela aceita explicitamente a estrutura preservada e o início imediato, registrar essa aprovação no mesmo request e avançar os gates técnicos restantes; não exigir outro OK comercial só porque houve manutenção ou geração do horário técnico de execução. Tratar também uma ordem explícita de ativar o quanto antes, sem nova pergunta de horário, como definição do início deste pedido — não como uma lacuna que reaparece quando o horário antigo vence. Conferir a delegação aplicável, autenticar mensagem/autor e preservar a aprovação dos demais campos.
4. Preservar o resumo e o selo anteriores ao materializar uma alteração autorizada. Registrar a supersessão temporal no checkpoint e no mesmo dono de execução, informando também a manutenção dependente; marcar a orientação antiga de pedir horário como supersedida, pois um handoff histórico não pode reintroduzir uma pergunta já respondida. Manter orçamento, Page, mídia, copy, JSON e estrutura aprovados. Separar mudança de intenção do operador de suporte real do runner: aprovação de início imediato não prova que a revisão ou continuação após writes parciais já é executável. Classificar essa lacuna como prontidão técnica, não como falta de autorização humana, e não lançar outro writer. A mecânica de horário vencido pertence à skill `meta-campaign-engine-v3`: carregar sua referência **Manifest and commands**, seção **Retomada com início vencido**.

### Corte e ROAS

A família define isolamento, idempotência, proveniência, lane de corte e lane de reativação. Thresholds, comparadores, fases, horários, níveis de write, métricas e budgets são parâmetros obrigatórios da operação.

### Diário

Rota read-only. Período, schedule, fontes, joins, métricas, renderer e postagem automática são definidos por operação. Ausência, staleness ou ambiguidade vira `N/D`, nunca zero inventado.

### Page e limites

A família exige identidade exata, freshness, plano idempotente, fail-closed e readback. Métrica, threshold, Page policy, hold, ações e schedules pertencem à operação.

## Invariantes de execução

- Original e tratado são uma única linhagem criativa.
- Criação e clone usam somente o Campaign Engine v3.
- Mídia nova é enviada para a Meta somente depois que o pedido resolve a conta exata; BOT exige vertical+square e usa pipeline paralelo. Reconciliar títulos determinísticos uma vez por lote, reutilizar variante parcial, subir somente a ausente, dividir wait-ready em chunks de 50 e verificar associação uma vez antes de gravar o registry. Nunca pre-stage global ou upload para contas inferidas.
- BOT não pode depender de importar/atribuir o acervo de aproximadamente 3 mil Pages a um Business Manager. Cada perfil anunciante usa seu próprio User Access Token porque é essa identidade que enxerga as Pages linkadas; System User, token compartilhado ou token de outro anunciante são fallbacks proibidos. Resolver somente o `pg_XXXXX` pedido, obter `access_token` por GET direto da Page, mantê-lo apenas em memória, validar PBIA e remover o token antes de persistir state/audit.
- Todo write exige autoridade, pre-read, request persistido e GET/readback.
- Falha após possível efeito parcial inicia recovery readback-first; nunca repetir POST às cegas.
- `ACTIVE` não prova serving; exigir impressão, gasto ou insight real quando a afirmação for de entrega.
- Credenciais, IDs técnicos extensos e billing permanecem fora do texto humano.
- Cron é gatilho, não fonte de estratégia, e segue a política global anti-colisão.
- Configuração do ChatPion/DigitalTrChat permanece fora do escopo padrão do Ares.

## Sincronização das threads

Uma alteração durável aprovada inclui, no mesmo request, a atualização das projeções Discord correspondentes; não exige uma segunda confirmação apenas para refletir a regra já aprovada.

1. Classificar `family` ou `operation`.
2. Persistir e validar primeiro a fonte canônica.
3. Executar `scripts/ares-chatpion-bot-strategy-sync.py --scope operation --operation <operation_id> --route <rota>` para validar o binding e as rotas, sem flags de escrita. Não usar `--check`, que não pertence a esse CLI. Para escopo de família, selecionar `--scope family`; conferir separadamente a igualdade fonte/versionado/runtime e as projeções no resultado da sincronização.
4. Atualizar prompt/config local da operação.
5. Projetar a mudança na rota funcional afetada e em `rules`.
6. Fazer GET/readback de cada mensagem criada/editada.
7. Persistir IDs/digests e audit da projeção.

A sincronização edita somente a mensagem de projeção controlada pelo Ares. Mensagens humanas, eventos de sistema, rotas e histórico não são deletados. Limpeza destrutiva exige autorização própria e não faz parte do sincronizador.

## Onboarding de nova operação

1. Registrar identidade, ownership, escopo e autoridade sem copiar state da fonte. Separar vínculo da thread, aprovação de onboarding, delegação financeira/ativação e OK final do request; uma camada não comprova as demais. Interpretar uma confirmação curta pelo pedido de aprovação ao qual ela responde, sem usá-la para resolver outra pergunta pendente de horário.
2. Validar conta e capabilities em read-only, incluindo Business, moeda e timezone. Resolver a Page pela hierarquia da campanha exata. Acesso à conta não comprova acesso à Page nem identifica, sozinho, o perfil anunciante correto; não transformar um token que lê a conta em credencial operacional por conveniência.
3. Criar contrato isolado começando fail-closed. Se houver cadastro parcial, manter o consumidor como candidato, sem modos executáveis ou credencial presumida, até validar as dependências. Registrar separadamente autoridade aprovada e readiness pendente, para não cobrar novamente uma autorização já concedida. Receita e aceite: `references/operation-contract-schema.md`, seção de cadastro parcial.
4. Registrar threads, prompts e membros obrigatórios sem alterar consumidores ou rotas de outras contas.
5. Validar relatórios read-only e as dependências necessárias à modalidade solicitada; não usar erro de Page como prova automática de scope ausente nem ampliar permissões no onboarding sem o gate próprio.
6. Preparar criação/clone por manifest somente após readiness. Manter o request original e os parâmetros literais durante a preparação; resolver ambiguidades comerciais e apresentar o resumo para OK antes do write.
7. Executar canário somente com autorização específica e distinguir status configurado de serving comprovado.
8. Liberar controlled-write somente após os gates aplicáveis e verificar que contas e consumidores preexistentes permaneceram inalterados.
9. Liberar automação por último, após inventário de cron e autorização própria. No fechamento, distinguir cadastro salvo, validação read-only, execução liberada e campanha efetivamente criada; configuração parcial nunca é onboarding concluído.

Nunca herdar implicitamente IDs, budgets, thresholds, Pages, pixels, eventos, JSON, horários, denylist, holds, baselines ou autonomia financeira.

## Verification

- skill e contrato da família não contêm identidade de consumidor;
- consumidor resolve para um único contrato e conjunto de threads;
- onboarding parcial permanece candidato e falha antes do transporte; autoridade aprovada não é confundida com readiness ou OK de publicação;
- conta e Page são verificadas separadamente, e a contagem da hierarquia vem da API, não do nome da campanha;
- nome corrigido reaproveita o mesmo request e exige GET vivo; anúncio-fonte recém-disponível PAUSED/IN_PROCESS elimina somente o bloqueio de ausência, sem ativar a original nem remover outros gates;
- nome operacional + ID com nota interna entre parênteses mantém o mesmo binding e não cria alias a partir da nota;
- definição de finalidade da thread não dispara execução, e correção de nota interna não altera a conta nem outras threads;
- cada parâmetro obrigatório tem origem explícita na operação;
- mudança de operação afeta somente um consumidor;
- mudança de família valida todos os consumidores ativos;
- rota funcional e Regras têm projeção com digest/readback;
- existe somente uma versão ativa por chave canônica;
- testes de arquitetura, prompts e operação passam sem Meta write.
