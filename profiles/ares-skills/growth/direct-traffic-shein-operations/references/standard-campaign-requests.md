# Padrões oficiais de nome e pedido — SHEIN-US-DIRECT

## Versão humana compacta 3.0 — aprovada por Rodolfo

A versão 3.0 foi aprovada por `exato, pode salvar` na thread `1557274000680288307`. Substitui a 2.0: título `Suba essa campanha`, sem linhas Modo/Quiz, campos e ordem fixos, fonte e escolha de criativos determinam a intenção. Histórico de formulários permanece abaixo, explicitamente supersedido. Aprovação documental não habilita campos ainda pendentes no runner.

### Nome aprovado

```text
Nº CAMPANHA - DATA - QUIZ - PRODUTO - LANCE - (TRACKING) - event_add_to_wishlist
```

- DATA é o início configurado no timezone da conta, em DD/MM.
- Nº CAMPANHA é o sequencial resolvido por conta e vem primeiro; DATA vem depois. Essa ordem supersede a proposta anterior de data primeiro. O novo nome é sempre gerado neste padrão, inclusive quando o pedido diz duplicar/clonar igual; nunca copiar o nome da fonte como exceção.
- QUIZ é v1, v2 ou v3 ligado à URL real, nunca deduzido por substring do caminho. Sem mapa canônico, não inventar versão nem destino.
- PRODUTO é o produto real, coerente com mídia e copy.
- LANCE é somente MAXVOL, COCAP ou BIDCAP. Não incluir valor de cap nem USD no nome: valores podem mudar intraday.
- Complemento de cópia: duplicação/clonagem de referência acrescenta ` - COPY C<NÚMERO DA FONTE>` entre `(TRACKING)` e `add_to_wishlist`, sempre apontando à fonte direta do pedido. Ex.: `120 - 09/10 - v2 - FREE CLOTHES - MAXVOL - (b01fb01c120) - COPY C67 - event_add_to_wishlist`. Campanhas novas do zero não recebem COPY por apenas usar referência de configuração/copy. O padrão base permanece igual; COPY é um add-on, não parte do produto nem do tracking.
- Campanhas fonte existentes podem usar nomenclatura antiga. Não exigir o padrão novo na fonte, não renomear legado para satisfazer o preflight e não bloquear só por ausência de data/quiz/lance no nome antigo. Consultar os campos reais e a identidade necessária; aplicar o validador estrito apenas ao novo nome gerado.
- TRACKING mantém o identificador técnico entre parênteses; novos utm_campaign/utm_adgroup, nenhuma herança indevida da fonte.
- O evento visível é `event_add_to_wishlist` em minúsculas, com prefixo event_. Essa decisão posterior de Rodolfo supersede o rótulo anterior sem prefixo. O valor técnico da API permanece `ADD_TO_WISHLIST`; não alterar pixel/evento por capitalização do nome.

Exemplos ilustrativos, não campanhas criadas:

```text
115 - 08/10 - v2 - FREE CLOTHES - MAXVOL - (b01fb01c115) - event_add_to_wishlist
115 - 08/10 - v2 - FREE CLOTHES - COCAP - (b01fb01c115) - event_add_to_wishlist
115 - 08/10 - v2 - FREE CLOTHES - BIDCAP - (b01fb01c115) - event_add_to_wishlist
```

### Pedido aprovado

Apresentar pedidos e exemplos como blocos `text` com os mesmos campos, rótulos e ordem do modelo abaixo. Variar somente os valores; não substituir por frases corridas, enunciados livres ou um formato diferente por gestor. Não acrescentar linhas de status/execução redundantes. Para múltiplos modelos que serão copiados separadamente no Discord, enviar um bloco por resposta e numerar a sequência.

```text
Suba essa campanha

Conta: [nome completo da conta de anúncio]
Quantidade: [número de campanhas]

Campanha fonte: [número ou nome da campanha de referência]
Lance: Igual ao da fonte — MAXVOL, COCAP ou BIDCAP
Valor do lance: [valor para COCAP/BIDCAP / igual ao da fonte / não se aplica para MAXVOL]
Budget: [valor por campanha / igual ao da fonte]

Criativos: [manter os da fonte / novos do Drive — produto e quantidade por campanha]
Hora/Data início: [agora / data e hora no timezone da conta / omitir para 00:00 do dia seguinte]
```

- Valores SHEIN em USD, mantendo conferência da moeda real da conta antes do write. Budget diário por campanha é separado do valor de lance.
- Não exigir linha `Status final` nem `Execução: ativar após validar`: novos pedidos têm ACTIVE final por padrão após QA de todas as campanhas. A construção continua PAUSED. Acrescentar `deixar pausada para revisão` somente quando quiser essa exceção.
- `Duplicar igual` e `Clonar igual` são sinônimos de pure_clone e mantêm mídia/copy/configurações. A palavra clonar isolada não autoriza mídia nova. `Clonar com criativos novos`/`Duplicar com criativos novos` são clone_prestaged. Criar do zero é from_zero_prestaged; Ares resolve IDs/lineage internamente.
- Não exigir campos Modo ou Quiz neste pedido com referência. `Criativos: manter os da fonte` resolve pure_clone; `novos do Drive` resolve clone_prestaged, conservando copy/configurações e exigindo mídia aprovada/compatível. Herdar destino/quiz pela URL real da fonte sem pedir versão humana. Identificar v1/v2/v3 no nome somente com correspondência comprovada; não adivinhar a versão a partir do caminho.
- Para criar campanha/conjunto realmente do zero, a frase inicial deve dizer `Criar do zero`; uma referência pode servir de template/configuração/copy, mas não autoriza inferir esse modo somente por haver criativos novos. Não exigir IDs técnicos ao gestor.
- Conservar Ad setup e localização original do tracking; Create ad não vira post existente para preservar social proof automaticamente.
- Início `agora` autoriza o intent IMMEDIATE; datas humanas agendadas permanecem literais. Não usar `Preparar agora` como sinônimo silencioso de revisão PAUSED.

### Atalho de duplicação e início padrão

Com a conta resolvida por nome explícito ou contexto canônico inequívoco, `Duplicar a campanha 72` / `Clonar igual a campanha 72` é pedido suficiente: uma nova campanha, mesmas mídia/copy/estrutura/público/posicionamentos/pixel/evento/lance/valor de lance/budget/Ad setup/local do tracking/destino da fonte. Não pedir que o gestor repita esses valores. Nenhuma menção a mídia nova significa manter os criativos; não selecionar assets do Drive por conta própria.

Horário omitido usa **00:00 do próximo dia civil no timezone verificado da conta**, não do VPS. Resolver uma vez no preflight e preservar o início resolvido entre retomadas; não reagendar ao cruzar meia-noite. Data/hora ou `agora` expressos prevalecem. ACTIVE depois do QA habilita para a data agendada, não entrega antes dela. PAUSED/revisão expresso continua exceção.

`Igual` não é identidade dos objetos: novo número/nome/IDs/UTMs da campanha nova, com URL/CTA atualizadas para o novo tracking e mesma localização dos parâmetros. Não reaproveitar UTMs da fonte. Normalizações inevitáveis da Meta são declaradas, nunca chamar de literalmente idêntico se houver divergência. Estrutura não suportada é bloqueada/diagnosticada, não achatada silenciosamente.

Conta ausente ou ambígua não autoriza procurar o número em todas as contas ou cruzar gestores. Perguntar somente qual conta quando o contexto não a resolver. Este atalho é para nova duplicação, não altera campanhas existentes nem agenda recorrente.

### Estado real de implementação

- Já disponíveis: modos técnicos, budget da fonte, NOW, source setup/tracking, QA global e ACTIVE final padrão.
- Pendentes: escolhas de bid_strategy/bid_amount diferentes da referência por campo de pedido. Nomenclatura completa e modelo do quiz por rota corporativa verificada estão implementados no formatter; rotas não reconhecidas bloqueiam, não são adivinhadas.
- Salvar o padrão não instala essas pendências nem renomeia campanhas existentes. Não prometer suporte integral, não tratar campos como implementados e não executar canário por causa desta aprovação documental.

## Histórico supersedido — formulários 1.0

Os textos seguintes são histórico das especificações anteriores, não o formulário humano vigente.

A base dos três modelos foi aprovada por Rodolfo Mattei em 14/09/2026. As regras técnicas abaixo foram supersedidas nas correções posteriores da thread `1557274000680288307`: preservar Ad setup e localização do tracking, não preservar post/prova social automaticamente, e respeitar a lineage exigida pela conta. Os modelos humanos longos foram substituídos pela versão compacta 3.0 aprovada acima; a 2.0 com campos Modo/Quiz também está supersedida.

## Status padrão — nova decisão de Rodolfo

Em novos pedidos SHEIN, criar → validar todas as campanhas do pedido → ativar é o padrão autorizado. A linha de status/execução para ativação pode ser omitida; o backend materializa ACTIVE a partir da política canônica. PAUSED durante construção e QA é contenção técnica, não status final padrão. Deixar pausada para revisão só quando solicitado expressamente. Datas/horários agendados continuam sendo respeitados; falha de QA não libera ativação. Nenhuma campanha existente é reativada por essa mudança.

## Modo de criação não é estratégia de lance

- Modo: duplicar igual; clonar com criativos novos; criar do zero.
- Vocabulário SHEIN confirmado por Rodolfo: MAXVOL = Highest volume or value (nesta operação Add to Wishlist, volume sem cap); COCAP = Cost per result goal; BIDCAP = Bid cap. Preservar o alias COCAP literalmente no pedido humano, sem substituir por outro nome.
- MAXVOL não exige valor de lance. COCAP exige a meta de custo por resultado e moeda; BIDCAP exige o teto de lance e moeda, que não é um custo por resultado garantido. Budget diário é um valor separado.
- Duplicar igual herda a estratégia e o valor efetivos da fonte por API, não do nome da campanha. Se o pedido escolher outra estratégia ou outro valor, não chamar de duplicação igual nem executar silenciosamente como pure_clone.
- O runner atual herda estratégia/valor da referência; escolher uma estratégia diferente por campo de pedido ainda não está implementado. O novo pedido humano contém esse campo aprovado, mas sua implementação técnica continua pendente.

Estes são os três modelos humanos históricos supersedidos. Validações internas de conta, compatibilidade site/idioma e evento da fonte continuam obrigatórias no preflight do Ares, mas não devem ser acrescentadas ao texto que o gestor precisa preencher.

## 1. Criar do zero com criativos novos

```text
PEDIDO DE CAMPANHA — SHEIN
Modo: Criar do zero com criativos novos

Site/idioma: [DOMÍNIO] - [EN OU ES]
Conta: [NOME DA CONTA DE ANÚNCIO]

Quantidade de campanhas: [NÚMERO DE CAMPANHAS]
Estrutura por campanha: CBO 1×[CONJUNTOS]×[ANÚNCIOS] — Ex.: 1×1×3
Lance: [MAXVOL OU OUTRA ESTRATÉGIA]
Budget: [VALOR + MOEDA] por campanha
Criativos: [NÚMERO DE CRIATIVOS] [VÍDEOS OU IMAGENS] novos do Drive por campanha
Reutilizar o mesmo criativo: NÃO

Origem dos criativos:
- Google Drive — [SHEIN_US_EN OU SHEIN_US_ES]
- Usar linhagens distintas, liberadas e reconciliadas
- Produto/ângulos: [DEFINIDOS PELO ARES] OU [GESTOR ESCOLHE OS CRIATIVOS]
- Não cruzar criativos EN com ES

Copy:
- [USAR A COPY SHEIN APROVADA]
OU
- Primary text: [...]
- Headline: [...]
- Description: [...]
- CTA: [...]
[DEFINIDO PELO GESTOR]

Início: [AGORA OU DATA + HORA] — timezone da conta de anúncio
Ativação após QA: padrão automático; escrever “deixar pausada para revisão” somente quando quiser essa exceção.

REGRAS:

Objetivo/otimização/evento: padrão fixo SHEIN — Sales / Offsite Conversions / Add to Wishlist

Identidade e lineage:
- Não reutilizar source_campaign_id ou source_adset_id
- Ares resolve source_ad_id somente quando a conta exigir lineage técnica de anúncio; esse vínculo não reutiliza a campanha/conjunto nem os criativos da fonte
- Criar novos campaign_id, adset_id, ad_id, creative_id, effective_object_story_id e IDs de mídia
- Não reutilizar mídia, creative, post social ou prova social de outra campanha
- Registrar no audit o vínculo entre cada anúncio novo e o asset selecionado no Drive

Após concluir:
- Confirmar os novos campaign_id, adset_id, ad_id, creative_id, effective_object_story_id e IDs de mídia
- Informar estrutura, criativos, copy, UTMs, budget, início e status
- Apresentar o readback completo
- Medir preparação, mídia, Engine/API, readback, Drive/inventário e tempo total E2E
```

## 2. Clonar com criativos novos

```text
PEDIDO DE CAMPANHA — SHEIN
Modo: Clonar com criativos novos

Site/idioma: [DOMÍNIO] - [EN OU ES]
Conta: [NOME DA CONTA DE ANÚNCIO]

Quantidade de campanhas: [NÚMERO DE CAMPANHAS]
Criativos: usar [NÚMERO DE CRIATIVOS] [VÍDEOS OU IMAGENS] novos do Drive por campanha

Campanha fonte: [NOME EXATO OU ID DA CAMPANHA]

Manter da fonte:
- Estrutura
- Público
- Posicionamentos
- Pixel
- Objetivo e evento
- Estratégia de lance
- Attribution
- Copy: Primary text, Headline, Description e CTA

Criativos:
- Google Drive — [SHEIN_US_EN OU SHEIN_US_ES]
- Usar linhagens distintas, liberadas e reconciliadas
- Produto/ângulos: [DEFINIDOS PELO ARES] OU [GESTOR ESCOLHE OS CRIATIVOS]
- Não reutilizar os criativos da campanha fonte
- Não cruzar criativos EN com ES
- Não reutilizar criativos entre os clones

Início / Budget: [AGORA OU DATA + HORA] — timezone da conta de anúncio / [VALOR + MOEDA] por campanha
Ativação após QA: padrão automático; escrever “deixar pausada para revisão” somente quando quiser essa exceção.

REGRAS:

Objetivo/otimização/evento: padrão fixo SHEIN — OUTCOME_SALES / OFFSITE_CONVERSIONS / ADD_TO_WISHLIST

Identidade e lineage:
- Criar novos campaign_id, adset_id, ad_id, creative_id, effective_object_story_id e IDs de mídia
- Manter source_ad_id apontando diretamente para os anúncios correspondentes da campanha fonte
- Não reutilizar creative_id, effective_object_story_id, video_id ou image_hash da fonte
- Não preservar o post social ou a prova social da fonte
- Não formar cadeia entre clones; todos devem apontar diretamente para a campanha fonte informada
- Registrar no audit o mapeamento entre os anúncios-fonte e os anúncios novos

Tracking:
- Manter a mesma URL base e os parâmetros não UTM da fonte
- Usar o próximo número sequencial disponível
- Criar novas UTMs para cada campanha
- Não reutilizar utm_campaign ou utm_adgroup da fonte

Após concluir:
- Confirmar a campanha fonte utilizada
- Confirmar os novos campaign_id, adset_id, ad_id, creative_id, effective_object_story_id e IDs de mídia
- Confirmar source_ad_id apontando diretamente para os anúncios da fonte
- Informar estrutura, criativos, copy, UTMs, budget, início e status
- Apresentar o readback completo
- Medir preparação, mídia, Engine/API, readback, Drive/inventário e tempo total E2E
```

## 3. Duplicar igual uma campanha existente

```text
PEDIDO DE CAMPANHA — SHEIN
Modo: Duplicar igual uma campanha existente

Site/idioma: [DOMÍNIO] - [EN OU ES]
Conta: [NOME DA CONTA DE ANÚNCIO]

Quantidade de duplicações: [N]

Campanha fonte: [NOME EXATO OU ID DA CAMPANHA]

Início: [AGORA OU DATA + HORA] — timezone da conta de anúncio
Ativação após QA: padrão automático; escrever “deixar pausada para revisão” somente quando quiser essa exceção.
Budget: Utilizar o mesmo budget da campanha duplicada.

REGRAS:

Preservar exatamente:
- Estrutura
- Público
- Posicionamentos
- Pixel
- Objetivo e evento
- Estratégia de lance
- Attribution
- Copy: Primary text, Headline, Description e CTA
- Criativos/imagens/vídeos
- Ad setup e localização dos parâmetros de tracking
- URL base e parâmetros não UTM

Não selecionar ou consumir criativos novos do Drive.
Não trocar mídia ou copy.
Não cruzar campanhas ou criativos EN com ES.

Identidade e lineage:
- Criar novos campaign_id, adset_id, ad_id e creative_id
- Manter source_ad_id apontando diretamente para os anúncios correspondentes da campanha fonte
- Manter Create ad quando a fonte usa Create ad; materializar novo post se necessário para atualizar o Website URL
- Preservação do mesmo post/prova social não é automática; só com pedido expresso e compatibilidade comprovada com a nova URL/UTM
- Preservar os mesmos video_id ou image_hash da fonte quando a Meta mantiver esses identificadores
- Se a Meta rematerializar algum ID de mídia, comprovar a equivalência exata da mídia
- Não formar cadeia entre duplicações; todas devem apontar diretamente para a campanha fonte informada
- Registrar no audit o mapeamento completo entre os IDs da fonte e os IDs novos

Alterar somente:
- Próximo número sequencial disponível
- Naming da campanha e do conjunto
- UTMs para o novo número
- Criar novo creative_id com a definição correta para aplicar as novas UTMs, sem trocar o Ad setup nem mover parâmetros para outro campo

Após concluir:
- Confirmar equivalência de mídia e copy com a fonte
- Confirmar os novos campaign_id, adset_id, ad_id e creative_id
- Confirmar source_ad_id apontando diretamente para os anúncios da fonte
- Confirmar Ad setup, localização do tracking e link final de CTA/Website URL com os novos tokens; declarar posts novos quando rematerializados
- Confirmar os mesmos video_id ou image_hash; se a Meta rematerializar algum ID, comprovar a equivalência da mídia
- Informar UTMs, budget, início, status e readback completo
- Medir preparação, Engine/API, readback e tempo total E2E
```
