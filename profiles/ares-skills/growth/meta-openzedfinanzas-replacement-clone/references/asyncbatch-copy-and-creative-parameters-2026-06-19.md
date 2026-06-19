# Asyncbatch native copy + creative_parameters probes — Elena 7/1 — 2026-06-19

## Contexto

Rodolfo corrigiu a hipótese de que seria necessário app/API avançado: o agente de um amigo conseguia clonar campanha com as mesmas permissões de token. A investigação então voltou para rota/ordem/parâmetros de clone via API pública, sem UI/manual.

Source usada:

```text
Campaign: 120248940367540604 — Elena Santana - ES - ESP - (pg_22091) - 4
Adset:    120248940367380604
Ad:       120248940367500604
Conta:    act_1356770869843984
Graph:    v25.0; também testado v20.0 para asyncbatch
```

## Aprendizados duráveis

### 1. Asyncbatch oficial inicia sem `addrafts`

A rota documentada funciona para iniciar jobs:

```text
POST /v25.0/
-F asyncbatch=[
  {
    "method": "POST",
    "relative_url": "<ADSET_ID>/copies",
    "name": "copy_adset_1",
    "body": "campaign_id=<TARGET_CAMPAIGN_ID>&deep_copy=true&status_option=PAUSED..."
  }
]
```

Resultado validado:

```text
async_sessions retornadas: sim
capability/addrafts exigido: não nessa rota
```

Isso muda a leitura anterior: `addrafts` pode ser uma rota, mas não é a única rota API para clone/copy assíncrono.

### 2. Campaign `deep_copy` dentro de asyncbatch também executa, mas falha no creative antigo

Rota testada:

```text
POST /
asyncbatch=[{"method":"POST","relative_url":"120248940367540604/copies","body":"deep_copy=true&status_option=PAUSED..."}]
```

Resultado:

```text
async_session criada
job falhou 3858504
```

Erro:

```text
error_subcode: 3858504
error_user_title: El contenido no debería incluir mejoras estándar
error_user_msg: Incluir el campo de mejoras estándar en el contenido quedó obsoleto...
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-campaign-asyncbatch-deepcopy-20260619T154631Z.json
```

### 3. O bloqueio atual não é scope/token; é creative obsoleto

Todos os ads da source Elena carregam no creative:

```json
{
  "degrees_of_freedom_spec": {
    "creative_features_spec": {
      "standard_enhancements": {
        "enroll_status": "OPT_IN"
      }
    }
  }
}
```

Esse campo legado/obsoleto bloqueia native copy/deep copy.

### 4. `creative_parameters` é lido no nível de `/ad_id/copies`

Testes:

```text
/ad_id/copies sem creative_parameters         -> 3858504 standard_enhancements
/ad_id/copies com creative_parameters granular -> mudou para 1815765 messenger_doc inválido
/ad_id/copies com creative_parameter singular  -> continuou 3858504
```

Conclusão: usar **`creative_parameters` plural** no nível do ad copy tem efeito; `creative_parameter` singular não resolveu.

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-creativeparam-probe-20260619T154751Z.json
```

### 5. Depois de remover `standard_enhancements`, aparece o próximo problema: `messenger_doc`

Erro após `creative_parameters` plural:

```text
error_subcode: 1815765
error_user_title: Estás usando un enlace externo no válido
error_user_msg: Tu anuncio usa https://fb.com/messenger_doc/ como enlace. Este formato no es válido como destino de un sitio web externo.
```

Interpretação: o copy estava aceitando a sobrescrita parcial do creative, mas ainda herdava/validava o `asset_feed_spec.link_urls.website_url=https://fb.com/messenger_doc/` como se fosse website externo. O próximo passo não é mais insistir em `standard_enhancements`; é acertar o formato exato de `creative_parameters` para Click-to-Messenger, removendo `messenger_doc` da camada de website URL.

### 6. Override com `object_story_spec.video_data` ainda não passou

Tentativa de `creative_parameters` com:

```text
object_story_spec.page_id
video_data.video_id
call_to_action APPLY_NOW
app_destination MESSENGER
page_welcome_message is_user_editing=true
sem messenger_doc
sem standard_enhancements
```

Resultado:

```text
code=1 generic unknown error
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-adcopy-oss-override-probe-20260619T154912Z.json
```

## Ordem recomendada para próximos testes

1. Não voltar para `addrafts` como hipótese principal; asyncbatch público já inicia.
2. Não testar `campaign deep_copy` puro repetidamente; ele falha no mesmo creative legado.
3. Trabalhar em **1 ad isolado** antes de 2 adsets/6 ads.
4. Criar campaign shell PAUSED + adset temporário PAUSED apenas para destino do `/ad_id/copies`.
5. Testar `/ad_id/copies` com `creative_parameters` plural, mirando o formato correto de Click-to-Messenger:
   - sem `standard_enhancements`;
   - sem `asset_feed_spec.link_urls.website_url=https://fb.com/messenger_doc/`;
   - preservar `video_id`/assets;
   - usar CTA Messenger/click-to-message correto;
   - `page_welcome_message` com `is_user_editing=true`.
6. Só depois que 1 ad copy passar, repetir para 3 ads e então para os 2 adsets.

## Disciplina operacional aprendida

- Probes Meta copy/async devem ser **curtos e bounded**: timeout explícito, polling limitado, e cleanup imediato.
- Se um teste puder passar de 1 minuto, preferir script com `notify_on_complete`/background ou subagente; não deixar tool foreground parecer travado no Discord.
- Ao criar shells/copied campaigns para teste, sempre listar/validar e deletar shells vazias ou parciais.
- Não declarar bloqueio de permissão/app quando a evidência mostra que a rota executa e falha por payload/creative.
