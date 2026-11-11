# Consulta read-only de configuração Meta por nível

## Sequência de coleta

1. Resolver a conta pelo contexto e catálogo positivo da operação e obter o `token_item` do binding vigente. Usar Graph v26.0 com `ares-meta-common.py` e seu throttle/backoff. Exigir o gate da conta e ler `act_<account_id>?fields=id,name,business,currency,timezone_name`; validar BM, identidade, moeda e fuso antes dos filhos.
2. Para localizar a mais recente em operação, ler `act_<account_id>/campaigns` com `effective_status=["ACTIVE"]`, campos `id,name,status,effective_status,created_time,start_time,daily_budget` e limite bounded. Seguir `paging.cursors.after` enquanto houver `paging.next`; não imprimir nem salvar URLs de paginação com credenciais. Deduplicar por ID e ordenar por `created_time` em código. Se timestamps empatarem, reportar o lote/empate; número no nome pode identificar o maior número, não provar que foi criado depois.
3. Para comprovar entrega, ler `<campaign_id>/insights` com `fields=campaign_id,spend,impressions&date_preset=today`. Gasto/impressões positivos comprovam entrega no dia da conta, não necessariamente no segundo da consulta. Resposta vazia não comprova pausa.
4. Para a campanha selecionada, GET `<campaign_id>` com `id,account_id,name,status,effective_status,objective,buying_type,daily_budget,lifetime_budget,bid_strategy,special_ad_categories,created_time,start_time,stop_time`. Exigir `account_id` igual à conta autorizada.
5. Paginar `<campaign_id>/adsets` com `id,name,status,effective_status,daily_budget,lifetime_budget,bid_strategy,bid_amount,billing_event,optimization_goal,destination_type,promoted_object,targeting,attribution_spec,start_time,end_time,is_dynamic_creative,pacing_type`.
6. Paginar `<campaign_id>/ads` com `id,name,adset_id,status,effective_status,creative{id,name,object_type,effective_object_story_id},tracking_specs,conversion_domain,url_tags`. Associar cada anúncio ao conjunto pelo ID e deduplicar os creative IDs antes da próxima etapa.
7. Buscar somente os creatives selecionados por ID com `id,account_id,name,object_type,title,body,call_to_action_type,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,instagram_user_id,effective_object_story_id`. Conferir seu vínculo à conta. Extrair texto, título, descrição, CTA, vídeo/imagem, identidades e destino de `video_data`/`link_data`/`asset_feed_spec`, conforme o formato retornado.
8. Validar os destinos descobertos pelo checker de domínio antes de persistir ou exibir links. Preservar literalmente os parâmetros instalados e não reconstruí-los pelo nome da campanha. Guardar evidência sanitizada, horário e contagens por nível; não despejar payloads completos na conversa.

## Interpretação e QA

- Converter budgets e `bid_amount` da unidade menor aplicável à moeda com Decimal. Para USD, dividir por 100. Orçamento no nível campanha caracteriza orçamento de campanha; não atribuir o mesmo valor como orçamento próprio de cada conjunto.
- Ler `bid_strategy` no nível em que foi retornado e `bid_amount` no conjunto para explicar a meta de custo. Não apresentar Cost Cap como custo observado ou promessa de custo máximo por cada resultado.
- Separar `objective`, `optimization_goal` e `promoted_object.custom_event_type`. Traduzir AddToWishlist como adicionar à lista de desejos, não compra.
- Interpretar atribuição por `event_type` e `window_days`, incluindo visualização engajada de vídeo quando presente.
- Descrever `age_min`, `age_max`, `age_range`, `user_age_unknown` e `targeting_automation.advantage_audience` sem prometer que todas as sugestões do público Advantage+ são limites rígidos de entrega.
- Se `publisher_platforms`/posições não aparecerem em `targeting`, dizer “sem restrições explícitas retornadas pela API”; não alegar confirmação visual dos posicionamentos automáticos. Aplicar o mesmo cuidado a gênero, interesses e término ausentes.
- Traduzir `targeting.locales` só com mapping confiável. Validar que a consulta devolveu objetos de locale e os IDs pedidos; resultados de interesses, mesmo com HTTP 200 e nomes de idiomas, não comprovam o mapping. Se não houver confirmação, mostrar os códigos e a limitação em uma linha, sem repetir a mesma busca semanticamente incorreta.
- Ler as inscrições individuais em `degrees_of_freedom_spec.creative_features_spec`. Se o campo principal de Advantage+ Creative estiver OPT_OUT e houver recursos OPT_IN, descrever a configuração mista e listar os relevantes; nunca resumir como “tudo desligado”.

## Formato de entrega

- Abrir com conta/campanha, quantidades de conjuntos/anúncios e status consultados.
- Usar três blocos: **Campanha**, **Conjunto(s)** e **Anúncio(s)**. Mostrar orçamento/estratégia no primeiro; meta de custo, evento, público e atribuição no segundo; status, formato e diferenças de assets no terceiro.
- Reunir copy, CTA, identidades e tracking compartilhados em um único bloco, preservando o texto original. Não inferir o conteúdo visual somente do nome do vídeo.
- Incluir uma observação curta se o evento real contrariar uma interpretação comum do objetivo/nome. Encerrar com horário no fuso da conta e confirmação de consulta sem alterações.
