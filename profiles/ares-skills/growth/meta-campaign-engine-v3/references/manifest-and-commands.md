# Manifest and commands

## Manifest modes

```text
pure_clone              duplicate source semantics; use tracking-aware shallow shells + lineage ads when account policy requires
clone_prestaged         campaign/adset/ad copy lineage + media count approved by the operation
from_zero_prestaged     new campaign + adset + creatives + ads; no source campaign/adset IDs; optional ad-only lineage
```

O alcance do registry é específico ao modo: `pure_clone` reutiliza a definição criativa e a mídia da fonte e pode executar com registry vazio; novas UTMs podem rematerializar Creative IDs e Video IDs sem criar uma nova linhagem de asset. Os modos prestageados exigem registros `ready` na quantidade definida pela operação: CPV usa exatamente três por campanha; Eggbev `clone_prestaged` aceita de 1 a 5 e Eggbev `from_zero_prestaged` aceita exatamente 3 ou 5. `clone_prestaged` exige IDs fonte e usa `/copies`; `from_zero_prestaged` proíbe `source_campaign_id` e `source_adset_id`, exige objetos `campaign_create` e `adset_create` completos e usa somente os edges diretos `act_{account}`. Ele pode carregar `source_ad_id` somente em cada anúncio novo; contas `lineage_required_for_new_media`, como CAR 05/13, exigem esse campo não zero, enquanto contas `direct_and_lineage_verified` podem omiti-lo. Não é necessário prepopular o registry sem pedido: quando houver mídia crua, o próprio pedido autorizado executa pre-stage/upload/readback antes de materializar e selar o manifest.

Every campaign requires:

```text
idempotency_key
app_key
account_id
mode
name
start_time with timezone
status PAUSED or future ACTIVE
```

`pure_clone` exige `source_campaign_id`. `clone_prestaged` exige `source_campaign_id`, `source_adset_id`, anúncios na quantidade permitida pela operação e `source_ad_id` não zero em cada anúncio. `from_zero_prestaged` exige `campaign_create`, `adset_create`, a quantidade de anúncios prevista pela operação e ausência de source campaign/adset IDs; `source_ad_id` é opcional no schema e obrigatório por policy em contas que exigem lineage de anúncio para mídia nova. Para cada mídia prestageada: asset ID, checksum, vertical video ID, square video ID, `ready=true`, `upload_edge=ad_account_advideos` e `association_verified=true`.

Payloads containing `standard_enhancements` or external `https://fb.com/messenger_doc/` are rejected before transport.

## Commands

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-summary
```

Register media only after real Meta readback. Manual registration is for importing already-confirmed IDs; the v3 pre-stage uploader is separately gated by `media_upload_enabled=true` and `--confirm-upload`:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-register \
  --account-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-video-id <id> --square-video-id <id> --ready --confirm-readback

python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prestage-upload \
  --account-id <id> --page-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-file <file> --square-file <file> --confirm-upload
```

The v3 pre-stage uploader is active but still requires `--confirm-upload`, advertiser User Access Token, Page `ADVERTISE` identity, exact checksum, both Meta videos reaching ready and exact ID membership readback in `act_{AD_ACCOUNT_ID}/advideos` before registry commit. It never uploads campaign media to `/{PAGE_ID}/videos`. Manual registration requires `--confirm-readback` and the same ad-account association proof.

Build CPV manifests only when every campaign has three ready media records and the source creative templates are current. `--campaign-numbers` accepts 1–100 values; the planner chunks them into bundles of two automatically:

```text
# Clone com mídia prestageada
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py build-cpv \
  --assets-json <assets.json> \
  --source-snapshot-json <source-selection.json> \
  --mode clone_prestaged \
  --campaign-numbers 14,15 --operational-date YYYY-MM-DD \
  --request-id <unique-id> --status ACTIVE --output <manifest.json>

# Criação do zero com mídia prestageada
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py build-cpv \
  --assets-json <assets.json> \
  --source-snapshot-json <reference-selection.json> \
  --mode from_zero_prestaged \
  --from-zero-specs-json <explicit-create-specs.json> \
  --campaign-numbers 31 --operational-date YYYY-MM-DD \
  --request-id <unique-id> --status PAUSED --output <manifest.json>
```

No modo do zero, `source-snapshot-json` fornece templates/campos de referência já lidos. `source_campaign_id` e `source_adset_id` ficam fora das campanhas do manifest e nunca entram no executor; somente `source_ad_id` pode acompanhar cada anúncio novo quando a conta exigir lineage para serving. `from-zero-specs-json` contém `from_zero_specs[]`, cada item com `campaign_create` e `adset_create` completos.

Use `--status PAUSED` para canário solicitado ou preparação controlada de uma ativação explicitamente autorizada. A produção programada normal usa `ACTIVE` com `start_time` futuro selado; preparação PAUSED não autoriza ativação implícita.

### Duplicação CPV com ativação imediata autorizada

1. Leia fontes exatas e próxima sequência live; congele budget, conjunto, anúncios, copy, mídia, posts e tracking. Não use o builder `build-cpv` de mídia nova para uma duplicação igual: materialize o manifest `pure_clone` tracking-aware com `source_campaign_id`, `source_adset_id`, `adset_name` e os anúncios com `source_ad_id`.
2. Herdando o budget exato da fonte, omita `campaign_updates.daily_budget` quando a policy de `pure_clone` proibir updates; até reaplicar o mesmo valor é um campo extra rejeitado. Se o pedido exigir outro budget para a cópia, preserve a fonte e resolva uma etapa permitida de ajuste do alvo PAUSED, com autorização e GET, antes da ativação. Não altere o budget da fonte sem pedido nominal nem desligue a policy para acomodar o campo.
3. Verifique os enums aceitos pela operação antes de selar: `start_intent=IMMEDIATE` não é uma capacidade universal. Se o prevalidator o restringir a outro lifecycle, use a preparação nativa `status=PAUSED`, `start_intent=SCHEDULED` e `start_time` com buffer técnico mínimo validado; mantenha a autorização de ativação imediata no request. Não altere schema/config nem introduza espera noturna para contornar o gate.
4. Para preservar post com AFS, materialize `existing_post_two_phase` com post + pacote AFS completo e UTMs do destino; siga `existing-post-afs-recovery.md` para flags, normalização e QA. Execute `prevalidate --manifest <draft> --output <sealed>`, depois `plan --manifest <sealed>` e `execute --manifest <sealed> --confirm-execute`, sempre pelo executor central.
5. Após `COMPLETE_PAUSED`, releia a hierarquia real: a preparação pode deixar também conjuntos/anúncios PAUSED. Sob a coordenação da conta, habilite somente filhos faltantes autorizados enquanto o pai permanece PAUSED, confirme-os por GET e então ative a campanha por status write com GET final. Não repita o execute para obter ativação se a criação já concluiu, nem interprete `PENDING_REVIEW/IN_PROCESS` como filho configurado desligado.
6. Diferencie no resultado criação concluída, ativação confirmada e entrega observada em Insights. Um novo objeto ACTIVE não demonstra que a duplicação resolveu a falta de gasto. Não arme, desarme ou retome watchers e rotinas recorrentes por inferência; qualquer exceção de início precisa ser reconciliada com a política vigente da operação.

The builder emits `prevalidated=false`. Promote only through the deterministic prevalidator, which rechecks the media registry and seals a tamper-evident content digest:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prevalidate \
  --manifest <draft.json> --registry <media-registry.json> --output <sealed.json>
```

Any post-prevalidation change invalidates execute. Source, templates, media, budget, UTMs, names and future start must be final before sealing.

## Execute gate

Real execute requires all four:

```text
manifest.prevalidated = true
config.enabled = true
config.write_enabled = true
--confirm-execute
```

O config instalado está ativo sob guards de `development_access`: `enabled=true`, `write_enabled=true` e `media_upload_enabled=true`. Isso não remove os gates independentes de manifest selado, `--confirm-execute` ou `--confirm-upload`; `--offline-fake` é somente teste e nunca contata a Meta.
