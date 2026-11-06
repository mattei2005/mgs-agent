# Duplicação com recurso herdado habilitado — referência de rota

## Finalidade e autoridade

Usar em pedidos de **duplicar com os mesmos criativos**, dentro da conta, operação, site e canal autorizados, quando a fonte contém recursos como `image_background_gen=OPT_IN`. A política continua em `SHEIN-US-DIRECT.json#/creative_policy/standard_copy_inherited_background_policy`; esta referência descreve o aprendizado de rota, não uma nova permissão ou mudança de padrão.

Esclarecimento de Rodolfo nas mensagens `1568372702295883896` e `1568372959788269738`: os screenshots e a cópia manual serviram para identificar a operação equivalente da API. O próximo gestor não precisa repetir esse diagnóstico nem explicar novamente a renumeração das UTMs.

## Caminho identificado para preservar a configuração

1. Ler a fonte e seus anúncios com paginação completa. Resolver por lineage os `creative_id`, `effective_object_story_id`, mídia, copy, Page/Instagram, Ad setup e estados individuais dos recursos.
2. Distinguir **referenciar o criativo existente** de **recriar sua definição**. Na referência manual analisada, os anúncios novos apontaram para os mesmos creative IDs e posts da fonte. Não interpretar a marca de recurso herdado como instrução para pedir sua desativação ou selecionar um catálogo.
3. A etapa de referência comprovada usa `POST /<AD_ID_NOVO>` com `creative={"creative_id":"<CREATIVE_ID_EXISTENTE>"}`, dentro do executor central e dos IDs do pedido. Ela não envia o mapa inteiro dos aprimoramentos para recriação e não escreve no creative compartilhado. Não apresentar esse attach isolado como executor completo de duplicação.
4. Criação dos shells/anúncios, lineage, numeração, status e recuperação continuam no Campaign Engine v3 e no contrato da operação. Não criar writer paralelo, repetir cópias cegamente ou reutilizar identidades de pedidos concluídos/deletados.

## Regras normais que permanecem obrigatórias

- Novo número de campanha implica **novas UTMs automaticamente**, incluindo `utm_campaign`, `utm_adgroup` e os demais tokens dependentes; conservar o local original do tracking. Isso não exige nova orientação ou aprovação do operador.
- Preservar o recurso e trocar as UTMs são partes da **mesma entrega**. Se o caminho de referência conservar a URL da fonte, tratar a aplicação do novo destino como correção técnica interna, não como escolha de negócio ou ajuste manual a entregar ao gestor.
- Respeitar budget, lance, início e status do pedido. Pedido para hoje/agora segue a intenção imediata já autorizada, após QA/readback, sem nova pergunta de ativação apenas por atraso técnico.
- Conferir por GET no alvo a estrutura, lineage, mídia/copy, configuração dos recursos e as UTMs do número novo antes de concluir.

## Evidência e limite da comprovação

As comparações e os updates de referência foram comprovados em `data/ares/meta-ads/audit/shein/native-inheritance-1568295434081014004/manual-equivalence-receipt.json`. O teste seguinte consta em `data/ares/meta-ads/audit/shein/standard-copy-1568337081321791502/post-create-readback.json`.

Essas provas identificam a preservação por referência; não demonstram que `creative_id` combinado com novos `object_story_spec`/`url_tags` efetue um clone parcial. No teste, o destino novo não foi aplicado. Não reutilizar silenciosamente a UTM da fonte, editar um objeto compartilhado, afrouxar QA ou declarar uma implementação geral validada com base apenas neste registro. A mesma orientação de leitura e seleção vale para gestores autorizados; capacidades, contratos e parâmetros de outras operações precisam de validação própria.

Os canários C240/C241 foram excluídos por ordem de Rodolfo. Seus receipts são evidência histórica, nunca autorização para recriá-los ou reativá-los.
