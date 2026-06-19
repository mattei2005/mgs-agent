# Elena native/async copy probe — standard_enhancements + CTM blockers — 2026-06-19

## Context

Rodolfo informou que outro agente consegue clonar campanha Meta com as mesmas permissões do token, então Ares testou rotas/ordens de clone API sem pedir app advanced/full access.

Source principal:

```text
Campaign: 120248940367540604
Adset:    120248940367380604
Ad:       120248940367500604
Conta:    act_1356770869843984
Graph:    v25.0
```

## Confirmações positivas

```text
Rota                                  | Status
--------------------------------------|----------------------------------------
/campaign_id/copies raso               | cria campaign shell PAUSED
/act/ asyncbatch com /adset_id/copies  | cria async_sessions
/campaign_id/copies deep em asyncbatch | executa e falha dentro da sessão, não por capability
/ad_id/copies com creative_parameters  | creative_parameters é lido pela Meta
```

Isso confirmou que não é obrigatório usar `addrafts` para iniciar async copy. O bloqueio atual é payload/creative, não token scope simples.

## Bloqueios observados

```text
Erro       | Onde apareceu                                      | Interpretação
-----------|----------------------------------------------------|-----------------------------------------------
3858504    | campaign/adset/ad native deep/copy                 | source creative tem standard_enhancements obsoleto
1815765    | ad copy com creative_parameters granular           | messenger_doc tratado como website externo inválido
1443048    | object_story_spec video/link variants              | object_story_spec malformado para CTM
1443226    | video_data sem image_url/image_hash                | thumbnail obrigatório
code=1     | várias estruturas CTM alternativas                 | erro genérico Meta; payload não aceito
1885501    | adset copy shallow/sync batch                      | Meta revalida attribution e aceita só (1,0)
```

## Variantes testadas que falharam

- `campaign_id/copies deep_copy=true` dentro de asyncbatch.
- `campaign_id/copies deep_copy=true` com `creative_parameters` / `creative_parameter` tentando substituir `degrees_of_freedom_spec`.
- `adset_id/copies deep_copy=true` dentro de asyncbatch com DSA/regional.
- `ad_id/copies` com:
  - `creative_parameters` granular sem `standard_enhancements`;
  - `creative_parameter` singular;
  - `object_story_spec.video_data` + `app_destination=MESSENGER`;
  - `asset_feed_spec` sem link;
  - `destination_spec.destination_type=SHOPS_MESSAGING` / `SHOPS_MESSAGING_OPT_OUT` / `WEBSITE_AND_SHOP` / `WEBSITE_AND_SHOP_OPT_OUT`;
  - `message_destination.page_id` (rejeitado como chave inesperada);
  - `message_destination.template_id` usando template_id da source (rejeitado como Page Welcome Message Template ID inválido);
  - `object_story_spec.link_data.page_welcome_message`;
  - `template_data` / `video_data` com page welcome interno.
- sync `batch` com campaign copy + dependent adset copy: result substitution não foi aceito no `campaign_id` e/ou adset copy voltou 1885501.

## Operational lesson

O caminho mais próximo da rota correta é async/native copy, mas a source Elena usa creatives com `degrees_of_freedom_spec.creative_features_spec.standard_enhancements=OPT_IN`, campo obsoleto que quebra deep copy pública. `creative_parameters` no nível do ad é lido, mas ainda não foi encontrado o formato CTM que substitui simultaneamente `standard_enhancements` e `messenger_doc` sem cair em erro genérico.

## Audits principais

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-campaign-asyncbatch-deepcopy-20260619T154631Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-creativeparam-probe-20260619T154751Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-oss-override-probe-20260619T154912Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-destspec-allowed-20260619T161119Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-destspec-template-20260619T161242Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-linkdata-welcome-20260619T161554Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-asyncbatch-chain-copy-20260619T161733Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-syncbatch-chain-copy-20260619T161840Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-campaign-deepcopy-creativeparams-20260619T161951Z.json
```

## Cleanup rule

Todos os objetos de teste devem ser criados PAUSED e deletados/verificados. Alguns deletes retornam PAUSED no primeiro GET imediatamente após o POST; repetir GET/DELETE após 2–3s até `status/effective_status=DELETED` antes de reportar limpeza.

## Next useful inputs

Se Rodolfo conseguir o payload/ordem do agente do amigo, comparar especialmente:

```text
Campo/rota a comparar
---------------------
endpoint exato usado para clone
uso de asyncbatch vs batch vs copies
creative_parameters exato
formato CTM/page_welcome_message
destination_spec/message_destination/template_id
como remove/substitui standard_enhancements
se usa ad draft interno sem chamar /addrafts explicitamente
```
