# Asyncbatch copy + CTM creative_parameters probe — Elena 7/1 — 2026-06-19

## Contexto

Rodolfo corrigiu a hipótese de que seria necessário app/API avançado: outro agente clona com as mesmas permissões de token. Ares então testou rotas de API pública em ordem mais próxima de clone/copy nativo, sem UI/manual.

Source principal:

```text
Campaign: 120248940367540604
Adset:    120248940367380604
Ad:       120248940367500604
Conta:    act_1356770869843984
Graph:    v25.0
```

## Correção de entendimento

`/act_<ID>/addrafts` não é o único caminho para cópia assíncrona. A rota oficial abaixo aceita iniciar jobs com o app/token atual:

```text
POST /<VERSION>/
-F asyncbatch=[{"method":"POST","relative_url":"<object_id>/copies", ...}]
```

Isso cria `async_sessions` sem `addraft_id`.

## Testes e resultados

```text
Rota / variante                                  | Resultado
-------------------------------------------------|------------------------------------------------
Campaign deep_copy dentro de asyncbatch          | falhou 3858504 standard_enhancements
Adset deep_copy dentro de asyncbatch             | cria async_sessions; falha 3858504 ou erro transitório
Ad copy sem creative_parameters                  | falha 3858504 standard_enhancements
Ad copy + creative_parameters granular           | creative_parameters é lido; erro muda para messenger_doc inválido
Ad copy + object_story_spec.video_data CTM       | code=1 genérico ou object_story_spec inválido
Ad copy + asset_feed_spec sem link               | code=1 genérico
Ad copy + destination_spec=MESSAGE/MESSENGER     | inválido; Meta lista valores aceitos de shops
Ad copy + destination_spec=SHOPS_MESSAGING       | message_destination não aceita page_id
Ad copy + template_id source                     | template_id não é Page Welcome Message Template ID válido
```

Audits principais:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-campaign-asyncbatch-deepcopy-20260619T154631Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-creativeparam-probe-20260619T154751Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-oss-override-probe-20260619T154912Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-single-ctm-adcopy-20260619T155808Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-two-short-ctm-adcopy-20260619T155858Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-afs-destination-20260619T160725Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-destspec-allowed-20260619T161119Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-destspec-template-20260619T161242Z.json
```

Todos os objetos temporários foram criados `PAUSED` e removidos/verificados `DELETED` quando não houve sucesso.

## Achados duráveis

1. **Asyncbatch é caminho real a manter no playbook.** Quando `/campaign_id/copies deep_copy=true` falha por limite `<3 objects`, testar o mesmo copy dentro de `asyncbatch` antes de concluir capability/addraft.
2. **O blocker atual do clone perfeito Elena não é token/scope.** A API chega na camada de copy, mas falha nos criativos CTM legados.
3. **`standard_enhancements` é o primeiro bloqueio do copy.** Source creatives Elena têm `degrees_of_freedom_spec.creative_features_spec.standard_enhancements=OPT_IN`; cópia nativa direta falha com `3858504`.
4. **`creative_parameters` deve ser aplicado no nível `ad_id/copies`.** No adset/campaign deep copy não resolveu. No ad copy individual, o override é lido porque o erro muda de `3858504` para erros de Messenger/`messenger_doc`.
5. **Não usar `destination_spec.message_destination.page_id`.** A API rejeita `page_id` como chave inesperada. Fields públicos mostram `message_destination.template_id`, mas o template ID embutido no `asset_feed_spec.additional_data.page_welcome_message` da source não é aceito como Page Welcome Message Template ID.
6. **`destination_spec.destination_type=MESSENGER` não é aceito.** Valores aceitos retornados pela Meta nesse contexto: `SHOPS_MESSAGING`, `SHOPS_MESSAGING_OPT_OUT`, `WEBSITE_AND_SHOP`, `WEBSITE_AND_SHOP_OPT_OUT`.
7. **Clone funcional segue possível.** Ares já consegue criar clone funcional 2 adsets/6 ads com attribution `1-day click`; isso não é clone perfeito se source usa `7-day click + 1-day view`.

## Próximo caminho recomendado

Para continuar a busca do clone perfeito:

```text
Prioridade | Próximo teste
-----------|-------------------------------------------------------------
1          | Testar object_story_spec.link_data com page_welcome_message interno, pois docs listam page_welcome_message como subcampo de link_data
2          | Testar copiar/gerar Page Welcome Message Template válido antes do ad copy, se existir endpoint público para isso
3          | Pedir ao amigo/buyer o payload exato ou HAR sanitizado da chamada de clone que funciona, principalmente creative_parameters/destination_spec
4          | Evitar repetir deep_copy puro sem override; ele volta para 3858504
```

## Comunicação operacional

Quando Rodolfo perguntar se já dá para clonar:

```text
Tipo de clone                  | Status
-------------------------------|-----------------------------------------------
Clone funcional/teste           | sim, 2 adsets/6 ads, PAUSED, mas attribution 1-day click
Clone perfeito 100% source      | ainda não; falta preservar 7/1 e resolver CTM creative copy
```

Não chamar clone funcional de “perfeito”.
