# Pedidos-padrão oficiais — SHEIN-US-DIRECT

Aprovados por Rodolfo Mattei em 14/09/2026 na thread Discord `1548765865258917969`.

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

Início / Status: [DATA + HORA] — timezone da conta de anúncio / [ACTIVE OU PAUSED]

REGRAS:

Objetivo/otimização/evento: padrão fixo SHEIN — Sales / Offsite Conversions / Add to Wishlist

Identidade e lineage:
- Não reutilizar source_campaign_id, source_adset_id ou source_ad_id
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

Início / Status / Budget: [DATA + HORA] — timezone da conta de anúncio / [ACTIVE OU PAUSED] / [VALOR + MOEDA] por campanha

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

Início / Status: [DATA + HORA] — timezone da conta de anúncio / [ACTIVE OU PAUSED]
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
- Post social e prova social
- URL base e parâmetros não UTM

Não selecionar ou consumir criativos novos do Drive.
Não trocar mídia ou copy.
Não cruzar campanhas ou criativos EN com ES.

Identidade e lineage:
- Criar novos campaign_id, adset_id, ad_id e creative_id
- Manter source_ad_id apontando diretamente para os anúncios correspondentes da campanha fonte
- Manter o mesmo effective_object_story_id da fonte para preservar o post social e a prova social
- Preservar os mesmos video_id ou image_hash da fonte quando a Meta mantiver esses identificadores
- Se a Meta rematerializar algum ID de mídia, comprovar a equivalência exata da mídia
- Não formar cadeia entre duplicações; todas devem apontar diretamente para a campanha fonte informada
- Registrar no audit o mapeamento completo entre os IDs da fonte e os IDs novos

Alterar somente:
- Próximo número sequencial disponível
- Naming da campanha e do conjunto
- UTMs para o novo número
- Criar novo creative_id exclusivamente para aplicar as novas UTMs, preservando o mesmo post social

Após concluir:
- Confirmar equivalência de mídia e copy com a fonte
- Confirmar os novos campaign_id, adset_id, ad_id e creative_id
- Confirmar source_ad_id apontando diretamente para os anúncios da fonte
- Confirmar o mesmo effective_object_story_id, post social e prova social da fonte
- Confirmar os mesmos video_id ou image_hash; se a Meta rematerializar algum ID, comprovar a equivalência da mídia
- Informar UTMs, budget, início, status e readback completo
- Medir preparação, Engine/API, readback e tempo total E2E
```
