# Pedidos-padrão oficiais — SHEIN-US-DIRECT

A base dos três modelos foi aprovada por Rodolfo Mattei em 14/09/2026. As regras técnicas abaixo foram supersedidas nas correções posteriores da thread `1557274000680288307`: preservar Ad setup e localização do tracking, não preservar post/prova social automaticamente, e respeitar a lineage exigida pela conta. Isso corrige a documentação existente; qualquer novo modelo curto apresentado para revisão continua sendo proposta até confirmação do operador.

## Status padrão — nova decisão de Rodolfo

Em novos pedidos SHEIN, criar → validar todas as campanhas do pedido → ativar é o padrão autorizado. A linha de status/execução para ativação pode ser omitida; o backend materializa ACTIVE a partir da política canônica. PAUSED durante construção e QA é contenção técnica, não status final padrão. Deixar pausada para revisão só quando solicitado expressamente. Datas/horários agendados continuam sendo respeitados; falha de QA não libera ativação. Nenhuma campanha existente é reativada por essa mudança.

## Modo de criação não é estratégia de lance

- Modo: duplicar igual; clonar com criativos novos; criar do zero.
- Vocabulário SHEIN confirmado por Rodolfo: MAXVOL = Highest volume or value (nesta operação Add to Wishlist, volume sem cap); COCAP = Cost per result goal; BIDCAP = Bid cap. Preservar o alias COCAP literalmente no pedido humano, sem substituir por outro nome.
- MAXVOL não exige valor de lance. COCAP exige a meta de custo por resultado e moeda; BIDCAP exige o teto de lance e moeda, que não é um custo por resultado garantido. Budget diário é um valor separado.
- Duplicar igual herda a estratégia e o valor efetivos da fonte por API, não do nome da campanha. Se o pedido escolher outra estratégia ou outro valor, não chamar de duplicação igual nem executar silenciosamente como pure_clone.
- O runner atual herda estratégia/valor da referência; escolher uma estratégia diferente por campo de pedido ainda não está implementado. Um modelo contendo essa troca é proposta de contrato, não capacidade produtiva declarada.

Estes são os três modelos humanos finais. Validações internas de conta, compatibilidade site/idioma e evento da fonte continuam obrigatórias no preflight do Ares, mas não devem ser acrescentadas ao texto que o gestor precisa preencher.

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
